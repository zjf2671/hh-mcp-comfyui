import os
import json
import logging
from pathlib import Path
import base64
from typing import Optional, Dict, Any, Union

from pydantic import HttpUrl, Field

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base as prompt_base

# Import the client logic
try:
    from . import comfyui_client
except ImportError:
    # Allow running directly for testing
    from hh_mcp_comfyui import comfyui_client

# Enhanced logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server with longer timeout (300 seconds)
mcp = FastMCP(
    "ComfyUI_Generator",
    version="0.1.0",
    description="MCP Server to generate images using a local ComfyUI instance.",
    timeout=300  # Increase timeout to 300 seconds (5 minutes)
)

# --- Resource Loading ---

# Dynamically load workflows as resources
workflow_dir = Path(os.getenv("COMFYUI_WORKFLOWS_DIR", Path(__file__).parent / "workflows"))

if not workflow_dir.is_dir():
    logger.warning(f"Workflows directory not found: {workflow_dir}. No workflow resources will be loaded.")
else:
    logger.info(f"Scanning for workflows in: {workflow_dir}")
    for filename in os.listdir(workflow_dir):
        if filename.endswith(".json"):
            workflow_name = filename[:-5] # Remove .json extension
            resource_uri = f"workflow://{workflow_name}"
            file_path = workflow_dir / filename

            # Define a function scope for each resource
            def create_resource_func(path: Path):
                def get_workflow_resource() -> str:
                    """Returns the content of the workflow JSON file."""
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            # Load and dump to ensure valid JSON and consistent formatting
                            content = json.load(f)
                            return json.dumps(content, indent=2)
                    except FileNotFoundError:
                        logger.error(f"Resource file not found during read: {path}")
                        # This shouldn't happen if scanning worked, but handle defensively
                        return json.dumps({"error": "Workflow file not found."})
                    except json.JSONDecodeError:
                         logger.error(f"Invalid JSON in resource file: {path}")
                         return json.dumps({"error": "Invalid JSON in workflow file."})
                    except Exception as e:
                        logger.exception(f"Error reading resource file {path}: {e}")
                        return json.dumps({"error": f"Error reading workflow file: {e}"})
                return get_workflow_resource

            # Register the resource using the dynamically created function
            mcp.resource(resource_uri)(create_resource_func(file_path))
            logger.info(f"Registered resource: {resource_uri} -> {filename}")

# --- Tool Definition ---

@mcp.tool()
async def generate_image_from_text(
    prompt: str,  # 添加默认prompt值
    workflow_name: str,
    width: int = 1024,
    height: int = 1024,
    seed: Optional[int] = None  # Default seed value
) -> str:
    """
    Generates an image using ComfyUI based on the provided prompt and optional parameters.

    Args:
        prompt: The positive text prompt (It must be in English).
        workflow_name: The name of the workflow file (without .json) from the 'workflows' directory to use.
                    If None, uses the default workflow ('t2image_bizyair_flux').
        width: The desired width of the image (default: 1024).
        height: The desired height of the image (default: 1024).
    Returns:
        A URL to view the generated image.
    """
    logger.info(f"generate_image_from_text called with prompt='{prompt}', width={width}, height={height}, workflow='{workflow_name}'")
    try:
        # 1. Load the specified or default workflow
        workflow_data = comfyui_client.load_workflow(workflow_name)
        logger.info(f"Loaded workflow: {workflow_name}")

        # 2. Modify the workflow with user inputs
        modified_workflow = comfyui_client.modify_workflow(workflow_data, prompt, width, height, seed)
        logger.info(f"Modified workflow: {modified_workflow}")
        
        # 3. Generate the image using the modified workflow
        image_url = await comfyui_client.generate_image_async(modified_workflow)

        logger.info(f"Image generation successful, returning URL: {image_url}")
        return image_url
    except FileNotFoundError as e:
        logger.error(f"Workflow file error: {e}")
        return f"Error: Workflow '{workflow_name or comfyui_client.DEFAULT_WORKFLOW}' not found."
    except (ConnectionError, ValueError, RuntimeError) as e:
        logger.error(f"Image generation failed: {e}")
        # Provide a user-friendly error message
        return f"Error generating image: {e}"
    except Exception as e:
        logger.exception("Unexpected error during image generation tool execution.")
        return f"Error: An unexpected error occurred: {e}"

@mcp.tool()
async def generate_image_from_image(
    prompt: str,
    workflow_name: str, # Default to the I2I workflow
    image_path_or_url: Union[HttpUrl, str, bytes] = Field(..., description="URL, local path, or image data as bytes."),
    denoise: float = 1.0,
    seed: Optional[int] = None # Allow optional seed override
) -> str:
    """
    Generates an image using ComfyUI based on an input image (URL, local path, or bytes), prompt, and optional parameters.

    Args:
        prompt: The positive text prompt (It must be in English).
        workflow_name: The name of the I2I workflow file (without .json) to use (default: 'I2Image_bizyair_flux').
        image_path_or_url: The URL or local file path or image data as bytes of the input image.
        denoise: Denoising strength (0.0 to 1.0). Controls how much the original image influences the result. to use (default: '1.0')
        seed: Optional random seed for reproducibility.
    Returns:
        A URL to view the generated image or an error message.
    """
    # Ensure seed is an integer if provided, generate random if None
    final_seed = seed if seed is not None else comfyui_client.random.randint(1, 999999999)
    # Convert HttpUrl to string if necessary
    image_input = str(image_path_or_url) if isinstance(image_path_or_url, HttpUrl) else image_path_or_url

    # Check if image_path_or_url is base64 encoded
    if isinstance(image_path_or_url, str) and image_path_or_url.startswith("data:image"):
        try:
            # Extract base64 data
            header, encoded = image_path_or_url.split(",", 1)
            image_input = base64.b64decode(encoded)
            logger.info("Image data is base64 encoded, decoded successfully.")
        except Exception as e:
            logger.error(f"Error decoding base64 image data: {e}")
            return f"Error: Could not decode base64 image data: {e}"
    else:
        image_input = str(image_path_or_url) if isinstance(image_path_or_url, HttpUrl) else image_path_or_url

    logger.info(f"generate_image_from_image called with prompt='{prompt}', image='{image_input}', denoise={denoise}, workflow='{workflow_name}', seed={final_seed}")

    try:
        # 1. Load the specified I2I workflow
        workflow_data = comfyui_client.load_workflow(workflow_name)
        logger.info(f"Loaded I2I workflow: {workflow_name}")

        # 2. Modify the workflow with user inputs (including uploading the image)
        # Need a client_id for potential upload within modify_i2i_workflow
        client_id = str(comfyui_client.uuid.uuid4())
        modified_workflow = await comfyui_client.modify_i2i_workflow(
            workflow_data,
            prompt,
            image_input,
            denoise,
            final_seed,
            client_id=client_id # Pass client_id
        )
        logger.info("Modified I2I workflow successfully.")
        # logger.debug(f"Modified I2I workflow details: {json.dumps(modified_workflow, indent=2)}") # Optional: log the full workflow

        # 3. Generate the image using the modified workflow
        # generate_image_async handles queuing, waiting, and result extraction
        image_url = await comfyui_client.generate_image_async(modified_workflow) # generate_image_async already uses its own client_id internally for queueing

        logger.info(f"Image generation from image successful, returning URL: {image_url}")
        return image_url
    except FileNotFoundError as e:
        logger.error(f"Workflow file error: {e}")
        return f"Error: Workflow '{workflow_name}' not found."
    except (ConnectionError, ValueError, RuntimeError) as e:
        logger.error(f"Image generation from image failed: {e}")
        return f"Error generating image from image: {e}"
    except Exception as e:
        logger.exception("Unexpected error during image generation from image tool execution.")
        return f"Error: An unexpected error occurred: {e}"


# --- Prompt Definition ---

@mcp.prompt(name="Generate Image with ComfyUI")
def generate_image_prompt(
    prompt: str,
    width: Optional[int] = 1024,
    height: Optional[int] = 1024,
    workflow: Optional[str] = None
) -> list[prompt_base.Message]:
    """
    Provides a starting point for generating an image using the generate_image tool.
    """
    tool_call_args = {
        "prompt": prompt,
        "width": width or 1024, # Ensure default if None
        "height": height or 1024, # Ensure default if None
    }
    if workflow:
        tool_call_args["workflow_name"] = workflow

    # Construct a user message that might trigger the tool use
    user_message = f"Generate an image with the prompt: '{prompt}'"
    if width != 1024 or height != 1024:
        user_message += f", size {width}x{height}"
    if workflow:
        user_message += f", using workflow '{workflow}'"
    user_message += "."

    return [
        prompt_base.UserMessage(user_message),
        # Suggest the tool call to the LLM
        # Note: The LLM ultimately decides whether and how to call the tool.
        # This prompt just makes it easier.
        # We don't include a direct tool_code block here as FastMCP handles
        # the tool definition and invocation based on the @mcp.tool decorator.
        # The LLM should infer the tool call from the user message and the
        # available tool definition provided by the server.
    ]


# --- Server Execution ---
def main():
        # Ensure the workflows directory exists relative to this script
    # This helps if running the script directly for testing
    workflows_path = workflow_dir
    if not workflows_path.exists():
        try:
            workflows_path.mkdir()
            logger.info(f"Created missing directory: {workflows_path}")
            print(f"Created missing directory: {workflows_path}")
            print("Please ensure your workflow JSON files are placed inside this directory.")
        except Exception as e:
             logger.error(f"Failed to create workflows directory {workflows_path}: {e}")
             print(f"Error: Failed to create workflows directory {workflows_path}. Please create it manually.")


    logger.info("Starting ComfyUI MCP Server...")
    # Run using stdio transport by default
    # Use `mcp run comfyui_mcp_server/server.py` or `python comfyui_mcp_server/server.py`
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
