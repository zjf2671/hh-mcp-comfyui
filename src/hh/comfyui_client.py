import asyncio
import json
import uuid
import os
import random
import httpx
import time
# import websockets
import websocket
from urllib.parse import urlencode
from pathlib import Path
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COMFYUI_API_BASE = "http://127.0.0.1:8188"
WS_URL = f"ws://{COMFYUI_API_BASE.split('//')[1]}/ws"
WORKFLOWS_DIR = Path(__file__).parent / "workflows"
DEFAULT_WORKFLOW = "t2image_bizyair_flux.json" # Default workflow if none specified

# --- Workflow Loading and Modification ---

def load_workflow(workflow_name: Optional[str] = None) -> Dict[str, Any]:
    """Loads a workflow JSON file from the workflows directory."""
    if workflow_name is None:
        workflow_name = DEFAULT_WORKFLOW
        logger.info(f"No workflow name provided, using default: {DEFAULT_WORKFLOW}")

    # Sanitize workflow_name to prevent directory traversal
    workflow_name = os.path.basename(workflow_name)
    if not workflow_name.endswith(".json"):
        workflow_name += ".json"

    workflow_path = WORKFLOWS_DIR / workflow_name
    if not workflow_path.is_file():
        logger.error(f"Workflow file not found: {workflow_path}")
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
            logger.info(f"Loaded workflow: {workflow_name}")
            return workflow
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {workflow_path}: {e}")
        raise ValueError(f"Invalid JSON in workflow file: {workflow_path}")
    except Exception as e:
        logger.error(f"Error loading workflow {workflow_path}: {e}")
        raise

def find_node_by_class_type(workflow: Dict[str, Any], class_types: list[str]) -> Optional[str]:
    """Finds the first node ID matching any of the given class_types."""
    for node_id, node_data in workflow.items():
        if node_data.get("class_type") in class_types:
            return node_id
    return None
def find_latent_by_class_type(workflow: Dict[str, Any]) -> Optional[str]:
    """Finds the first node ID matching any of the given class_types."""
    LATENT_IMAGE_TYPES = [
        "EmptyLatentImage",  # Standard
        "BizyAir_CogView4_6B_Pipe",  # Custom variant
        "EmptyLatentImageAdvanced"  # Advanced variant
    ]
    return find_node_by_class_type(workflow, LATENT_IMAGE_TYPES)

def find_save_image_node(workflow: Dict[str, Any]) -> Optional[str]:
    """Finds the node ID for saving image by class type."""
    # Supported save image node class types
    SAVE_IMAGE_TYPES = [
        "SaveImage",  # Standard
        "SaveImageWithMetadata",  # With metadata
        "BizyAir_SaveImage"  # Custom
    ]
    
    # Find first node with supported save image type
    for node_id, node_data in workflow.items():
        node_class = node_data.get("class_type", "")
        if node_class in SAVE_IMAGE_TYPES:
            logger.debug(f"Found save image node: {node_id} (class: {node_class})")
            return node_id
    
    logger.warning("Could not find a suitable save image node in workflow")
    return None

def find_random_seed_node(workflow: Dict[str, Any]) -> Optional[str]:
    """Finds the node ID for random seed node by class type."""
    # Supported random seed node class types
    RANDOM_SEED_TYPES = [
        "BizyAir_RandomNoise",  # BizyAir custom
        "KSampler",  # Standard sampler
        "KSamplerAdvanced",  # Advanced variant
        "RandomNoise",  # Generic noise
        "RandomSeed",  # Generic seed
        "BizyAir_CogView4_6B_Pipe"  # CogView4
    ]
    
    # Find first node with supported random seed type
    for node_id, node_data in workflow.items():
        node_class = node_data.get("class_type", "")
        if node_class in RANDOM_SEED_TYPES:
            logger.debug(f"Found random seed node: {node_id} (class: {node_class})")
            return node_id
    
    logger.warning("Could not find a suitable random seed node in workflow")
    return None

def find_positive_prompt_node(workflow: Dict[str, Any]) -> Optional[str]:
    """Finds the node ID for the positive prompt by class type."""
    # Supported CLIP text encoder class types
    CLIP_ENCODER_TYPES = [
        "CLIPTextEncode",  # Standard
        "BizyAir_CLIPTextEncode",  # BizyAir custom
        "CLIPTextEncodeSDXL",  # SDXL variant
        "CLIPTextEncodeAdvanced",  # Advanced variant
        "BizyAir_CogView4_6B_Pipe"  # CogView4
    ]
    
    # Find first node with supported CLIP encoder type
    for node_id, node_data in workflow.items():
        node_class = node_data.get("class_type", "")
        if node_class in CLIP_ENCODER_TYPES:
            logger.debug(f"Found positive prompt node: {node_id} (class: {node_class})")
            return node_id
    
    logger.warning("Could not find a suitable positive prompt node in workflow")
    return None


def modify_workflow(workflow: Dict[str, Any], prompt: str, width: int, height: int, seed: Optional[int] = None) -> Dict[str, Any]:
    """Modifies the workflow with the given prompt, width, and height."""
    modified_workflow = workflow.copy() # Avoid modifying the original dict

    # Modify positive prompt
    positive_prompt_node_id = find_positive_prompt_node(modified_workflow)
    if positive_prompt_node_id and "inputs" in modified_workflow[positive_prompt_node_id]:
        modified_workflow[positive_prompt_node_id]["inputs"]["text"] = prompt
        logger.info(f"Set positive prompt in node {positive_prompt_node_id}")
    else:
        logger.warning("Could not find suitable CLIPTextEncode node for positive prompt.")
        # Consider raising an error or providing a more robust finding mechanism

    # Modify latent image size
    latent_image_node_id = find_latent_by_class_type(modified_workflow)
    if latent_image_node_id and "inputs" in modified_workflow[latent_image_node_id]:
        modified_workflow[latent_image_node_id]["inputs"]["width"] = width
        modified_workflow[latent_image_node_id]["inputs"]["height"] = height
        logger.info(f"Set width={width}, height={height} in node {latent_image_node_id}")
    else:
        logger.warning("Could not find EmptyLatentImage node to set dimensions.")
        # Consider raising an error if size modification is critical

    # Modify random seed
    random_seed_node_id = find_random_seed_node(modified_workflow)
    if random_seed_node_id and "inputs" in modified_workflow[random_seed_node_id]:
            # Handle different node types with different input field names
            node_class = modified_workflow[random_seed_node_id].get("class_type", "")
            seed_value = seed if seed is not None else random.randint(1, 999999999)
            
            if node_class == "KSampler":
                modified_workflow[random_seed_node_id]["inputs"]["seed"] = seed_value
            elif node_class == "BizyAir_RandomNoise":
                modified_workflow[random_seed_node_id]["inputs"]["noise_seed"] = seed_value
            else:
                # Default to 'seed' field if present
                if "seed" in modified_workflow[random_seed_node_id]["inputs"]:
                    modified_workflow[random_seed_node_id]["inputs"]["seed"] = seed_value
                elif "noise_seed" in modified_workflow[random_seed_node_id]["inputs"]:
                    modified_workflow[random_seed_node_id]["inputs"]["noise_seed"] = seed_value
            logger.info(f"Set random seed in node {random_seed_node_id}")

    # Modify save image filename_prefix
    save_image_node_id = find_save_image_node(modified_workflow)
    if save_image_node_id and "inputs" in modified_workflow[save_image_node_id]:
        current_date = datetime.now().strftime("%Y-%m-%d")
        modified_workflow[save_image_node_id]["inputs"]["filename_prefix"] = f"{current_date}/ComfyUI"
        logger.info(f"Set filename_prefix to date in node {save_image_node_id}")

    return modified_workflow

# --- ComfyUI API Interaction ---

async def queue_prompt_async(prompt_workflow: Dict[str, Any], client_id: str) -> str:
    """Submits a workflow to the ComfyUI queue via HTTP POST."""
    # Disable proxy for localhost requests
    import os
    os.environ['NO_PROXY'] = '127.0.0.1'
    
    payload = {"prompt": prompt_workflow, "client_id": client_id}
    headers = {'Content-Type': 'application/json'}
    url = f"{COMFYUI_API_BASE}/prompt"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status() # Raise exception for bad status codes
            result = response.json()
            if "prompt_id" not in result:
                raise ValueError("Invalid response from /prompt endpoint: 'prompt_id' missing")
            logger.info(f"Queued prompt with ID: {result['prompt_id']}")
            return result["prompt_id"]
        except httpx.RequestError as e:
            logger.error(f"HTTP request error to {url}: {e}")
            raise ConnectionError(f"Could not connect to ComfyUI API at {url}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {url}: {e.response.status_code} - {e.response.text}")
            raise ConnectionError(f"ComfyUI API returned error: {e.response.status_code}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response from {url}: {e}")
            raise ValueError("Invalid JSON response from ComfyUI API") from e

async def get_history_async(prompt_id: str) -> Dict[str, Any]:
    """Fetches the execution history for a given prompt_id."""
    url = f"{COMFYUI_API_BASE}/history/{prompt_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            history = response.json()
            if prompt_id not in history:
                 raise ValueError(f"Prompt ID {prompt_id} not found in history response.")
            logger.info(f"Fetched history for prompt ID: {prompt_id}")
            return history[prompt_id]
        except httpx.RequestError as e:
            logger.error(f"HTTP request error to {url}: {e}")
            raise ConnectionError(f"Could not connect to ComfyUI API at {url}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {url}: {e.response.status_code} - {e.response.text}")
            raise ConnectionError(f"ComfyUI API returned error: {e.response.status_code}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response from {url}: {e}")
            raise ValueError("Invalid JSON response from ComfyUI API") from e

# def wait_for_prompt_completion_new(ws_url: str, client_id: str, prompt_id: str) -> None:
#     """Connects to WebSocket and waits for the execution complete signal."""
#     uri = f"{ws_url}?clientId={client_id}"
#     ws = websocket.WebSocket()
#     ws.connect(uri)
#     while True:
#         out = ws.recv()
#         if isinstance(out, str):
#             message = json.loads(out)
#             if message['type'] == 'executing':
#                 data = message['data']
#                 if data['node'] is None and data['prompt_id'] == prompt_id:
#                     break #Execution is done
#         else:
#             # If you want to be able to decode the binary stream for latent previews, here is how you can do it:
#             # bytesIO = BytesIO(out[8:])
#             # preview_image = Image.open(bytesIO) # This is your preview in PIL image format, store it in a global
#             continue #previews are binary data
                



def wait_for_prompt_completion(ws_url: str, client_id: str, prompt_id: str) -> None:
    """Connects to WebSocket and waits for the execution complete signal."""
    uri = f"{ws_url}?clientId={client_id}"
    
    def on_message(ws, message):
        if isinstance(message, str):
            message = json.loads(message)
            msg_type = message.get('type')
            data = message.get('data', {})
            msg_prompt_id = data.get('prompt_id')

            if msg_type == 'status':
                status_data = data.get('status', {}).get('exec_info', {})
                logger.info(f"Queue status: {status_data}")
                
                # 添加超时判断逻辑
                if 'queue_remaining' in status_data and status_data['queue_remaining'] == 0:
                    ws.close()
                    logger.info("No remaining prompts in queue, closing WebSocket.")
            elif msg_type == 'progress':
                value = data.get('value', 0)
                max_val = data.get('max', 1)
                if max_val > 0 and msg_prompt_id == prompt_id:
                    logger.info(f"Progress for {prompt_id}: {value}/{max_val} ({(value/max_val)*100:.1f}%)")
            elif msg_type == 'executing':
                if data.get('node') is None and msg_prompt_id == prompt_id:
                    logger.info(f"Execution finished signal received for prompt ID: {prompt_id}")
                    ws.close()  # Execution is done for our prompt
            elif msg_type == 'execution_error' and msg_prompt_id == prompt_id:
                logger.error(f"Execution error for prompt {prompt_id}: {data}")
                raise RuntimeError(f"ComfyUI execution error: {data.get('exception_message', 'Unknown error')}")
            elif msg_type == 'execution_complete' and msg_prompt_id == prompt_id:
                logger.info(f"Execution complete signal received for prompt ID: {prompt_id}")
                ws.close()

    def on_error(ws, error):
        logger.error(f"WebSocket error: {error}")
        raise ConnectionError(f"WebSocket error: {error}")

    def on_close(ws, close_status_code, close_msg):
        logger.info("WebSocket connection closed")

    try:
        ws = websocket.WebSocketApp(uri,
                                  on_message=on_message,
                                  on_error=on_error,
                                  on_close=on_close)
        logger.info(f"Connecting to WebSocket: {uri}")
        ws.run_forever()
    except Exception as e:
        logger.error(f"Failed to connect to WebSocket {uri}: {e}")
        raise ConnectionError(f"Failed to connect to WebSocket {uri}") from e


def extract_output_info(history: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Extracts filename and subfolder from the history outputs."""
    outputs = history.get("outputs", {})
    for node_id, node_output in outputs.items():
        if "images" in node_output:
            images = node_output["images"]
            if images:
                # Return the first image found
                image_info = images[0]
                filename = image_info.get("filename")
                subfolder = image_info.get("subfolder", "") # Subfolder might be empty
                file_type = image_info.get("type", "output") # Usually 'output'

                if filename and file_type == 'output': # Ensure it's an output image
                    logger.info(f"Found output image: filename={filename}, subfolder={subfolder}")
                    return filename, subfolder
    logger.warning("No output image found in history.")
    return None

# --- Main Function ---

async def generate_image_async(workflow: Dict[str, Any]) -> str:
    """
    Generates an image using the provided workflow and returns the preview URL.
    """
    client_id = str(uuid.uuid4())
    logger.info(f"Starting image generation with client_id: {client_id}")

    try:
        prompt_id = await queue_prompt_async(workflow, client_id)
        wait_for_prompt_completion(WS_URL, client_id, prompt_id)
        history = await get_history_async(prompt_id)
        output_info = extract_output_info(history)

        if output_info:
            filename, subfolder = output_info
            # Construct the view URL
            query_params = {"filename": filename}
            if subfolder:
                query_params["subfolder"] = subfolder
            # Ensure type=output is included if needed, though often default
            # query_params["type"] = "output"
            view_url = f"{COMFYUI_API_BASE}/view?{urlencode(query_params)}"
            logger.info(f"Image generation successful. View URL: {view_url}")
            return view_url
        else:
            raise RuntimeError("Image generation completed but no output image found in history.")

    except (ConnectionError, ValueError, RuntimeError, FileNotFoundError) as e:
        logger.error(f"Image generation failed: {e}")
        # Re-raise or handle specific errors as needed for the MCP server
        raise
    except Exception as e:
        logger.exception("An unexpected error occurred during image generation.")
        raise RuntimeError("An unexpected error occurred during image generation.") from e

# Example Usage (for testing this module directly)
async def main():
    try:
        # Load and modify a workflow
        wf = load_workflow("t2image_bizyair_flux.json") # Or another workflow
        modified_wf = modify_workflow(wf, prompt="photo of a cute cat astronaut on the moon", width=1024, height=1024, seed=4266)

        # Generate the image
        image_url = await generate_image_async(modified_wf)
        print(f"Generated Image URL: {image_url}")

    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    # Ensure workflows directory exists for standalone testing
    if not WORKFLOWS_DIR.exists():
        WORKFLOWS_DIR.mkdir()
        print(f"Created directory: {WORKFLOWS_DIR}")
        # You might need to manually copy workflow files here for standalone test

    import asyncio
    asyncio.run(main())
