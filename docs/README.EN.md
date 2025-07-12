# ComfyUI MCP Service

[![English](https://img.shields.io/badge/English-Click-yellow)](README.EN.md)
[![简体中文](https://img.shields.io/badge/简体中文-点击查看-orange)](../README.md)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../LiCENSE)
[![smithery badge](https://smithery.ai/badge/@zjf2671/hh-mcp-comfyui)](https://smithery.ai/server/@zjf2671/hh-mcp-comfyui)

This is a ComfyUI image generation service based on Model Context Protocol (MCP), which generates images by calling a local ComfyUI instance through API.

## Features

- Provides image generation service via MCP protocol, enabling natural language to image generation
- Supports dynamic replacement of parameters like prompts and dimensions in workflows
- Automatically loads workflow files from the workflows directory as resources

## Update History
- [2025-06-29] Support the Flux Kontext image editing workflow
![edit-image-85457440acc11a9f386f8ef284fd62f2.jpg](https://image.harryzhang.site/2025/07/edit-image-85457440acc11a9f386f8ef284fd62f2.jpg)
- [2025-05-11] Added dynamic configuration for workflow file directory
- [2025-05-09] Added docker build method, supports Python 3.12+
- [2025-05-07] Added pip build method
- [2025-05-06] Changed project directory from src/hh to src/hh_mcp_comfyui, added uvx build method
- [2025-04-26] Added image-to-image and background removal sample workflows, and support for image-to-image tool
- [2025-04-20] Added text-to-image generation tool
 
## Results

- **Effect in Cherry Studio**
![image-b8f946109d63fe1ccb5e2d63933e3f9e.png](https://image.harryzhang.site/2025/07/image-b8f946109d63fe1ccb5e2d63933e3f9e.png)

- **Effect in Cline**
![cline_gen_image-48d8515e0b59cd313879c62a1546162d.png](https://image.harryzhang.site/2025/07/cline_gen_image-48d8515e0b59cd313879c62a1546162d.png)
![ComfyUI_00020_-d9171f87fc9e67fcc1966cdbfb952a0c.png](https://image.harryzhang.site/2025/07/ComfyUI_00020_-d9171f87fc9e67fcc1966cdbfb952a0c.png)

## Installation

**1. Ensure Python 3.12+ is installed**

**2. Use uv to manage Python environment:**
- Install uv:
  ```bash
  # On macOS and Linux.
  $ curl -LsSf https://astral.sh/uv/install.sh | sh

  # On Windows.
  $ powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

  # Update uv (optional):
  $ uv self update
  ```

## Test Run Service
- **uvx method**
  ```bash
  $ uvx hh-mcp-comfyui

  INFO:hh_mcp_comfyui.server:Scanning for workflows in: C:\Users\tianw\AppData\Local\uv\cache\archive-v0\dp4MTo0f1qL0DdYF_BYCL\Lib\site-packages\hh_mcp_comfyui\workflows
  INFO:hh_mcp_comfyui.server:Starting ComfyUI MCP Server...
  ```
- **pip method**
  ```bash
  $ pip install hh_mcp_comfyui
  
  $ python -m hh_mcp_comfyui

  INFO:hh_mcp_comfyui.server:Scanning for workflows in: F:\Python\Python313\Lib\site-packages\hh_mcp_comfyui\workflows
  INFO:hh_mcp_comfyui.server:Starting ComfyUI MCP Server...
  ```
**The above information indicates successful service startup**

## Usage
> **Ensure local ComfyUI instance is running (default address: http://127.0.0.1:8188) [ComfyUI Installation](https://github.com/comfyanonymous/ComfyUI.git)**

### Usage in Cherry Studio, Cline, Cursor and other clients

<details>
  <summary>uvx MCP Service Configuration</summary>

  ```bash
  {
    "mcpServers": {
      "hh-mcp-comfyui": {
        "command": "uvx",
        "args": [
          "hh-mcp-comfyui@latest"
        ],
        "env": {
          "COMFYUI_API_BASE": "http://127.0.0.1:8188",
          "COMFYUI_WORKFLOWS_DIR": "/path/hh-mcp-comfyui/workflows"
        }
      }
    }
  }
  ```
</details>

<details>
  <summary>pip MCP Service Configuration</summary>

  **First execute in command window: pip install hh_mcp_comfyui**

  ```bash
  {
    "mcpServers": {
      "hh-mcp-comfyui": {
        "command": "python",
        "args": [
          "-m",
          "hh_mcp_comfyui"
        ],
        "env": {
          "COMFYUI_API_BASE": "http://127.0.0.1:8188",
          "COMFYUI_WORKFLOWS_DIR": "/path/hh-mcp-comfyui/workflows"
        }
      }
    }
  }
  ```
</details>

<details>
  <summary>docker MCP Service Configuration</summary>
  
  ```bash
  {
    "mcpServers": {
        "hh-mcp-comfyui": {
            "command": "docker",
            "args": [
                "run",
                "--net=host",
                "-v",
                "/path/hh-mcp-comfyui/workflows:/app/workflows",
                "-i",
                "--rm",
                "zjf2671/hh-mcp-comfyui:latest"
            ],
            "env": {
              "COMFYUI_API_BASE": "http://127.0.0.1:8188"
            }
        }
    }
  }
  ```
</details>

## Copy Sample Workflows to Specified Workflow Directory:

  (**Important Note**: Use the following uvx or pip methods to find the location of your installation workflow directory, add the sample workflow to it, and then restart your MCP service)
- **uvx**
  ```bash
  $ uvx hh-mcp-comfyui
  ```
 ![image-2-f89caf964efbccdad7b6fa2672d1cac0.png](https://image.harryzhang.site/2025/07/image-2-f89caf964efbccdad7b6fa2672d1cac0.png)
- **pip**
  
   ```bash
  # First install dependencies
  $ pip install hh_mcp_comfyui
  $ python -m hh_mcp_comfyui
  ```
  ![image-3-03a069f40492fea9947a351b8707aa3f.png](https://image.harryzhang.site/2025/07/image-3-03a069f40492fea9947a351b8707aa3f.png)

## Testing

> **Use MCP Inspector to test server tools**
  
- **uvx method**
  ```bash
  $ npx @modelcontextprotocol/inspector uvx hh-mcp-comfyui
  ``` 
- **pip method**
  ```bash
  $ pip install hh_mcp_comfyui
  $ npx @modelcontextprotocol/inspector python -m hh_mcp_comfyui
  ``` 
 - **docker method**
    ```bash
    $ npx @modelcontextprotocol/inspector docker run --net=host -i --rm zjf2671/hh-mcp-comfyui
    ``` 

Then click connect as shown below to debug:
![image-1-44c6a003ee317093afe5a61cfe028720.png](https://image.harryzhang.site/2025/07/image-1-44c6a003ee317093afe5a61cfe028720.png)

## Usage Notes (Especially for those new to ComfyUI)

- The default workflow is `t2image_bizyair_flux`
- The default picture size is 1024x1024
- All JSON workflow files in the workflows directory are automatically loaded when the service starts
- If you are using the ** sample workflow in this project ** and need to download a plug-in comfyui, please check out for details: [Sample Workflow Plug-in Installation Tutorial](https://ziitefe2yxn.feishu.cn/wiki/PlSmwBbBWiA0iDkc07scb4EEnHc)
- If you use your local comfyui workflow, you must first ensure that your workflow can run normally in comfyui, and then you need to export the JSON format (API) and place it in your local `/path/hh_mcp_comfyui/workflows` directory

## Add New Workflows

1. Place workflow JSON files in `src/hh_mcp_comfyui/workflows` directory
  
    For uvx and pip startup methods, refer to 《**Copy Sample Workflows to Specified Workflow Directory**》 above

2. Restart service to automatically load new workflows

## Development

### Project Structure

```
.
├── .gitignore
├── .python-version
├── pyproject.toml
├── README.md
├── uv.lock
├── example/              # Example workflows directory
│   └── workflows/
│       ├── i2image_bizyair_sdxl.json
│       ├── t2image_bizyair_flux.json
│       ├── i2image_cogview4.json
│       └── t2image_sd1.5.json
├── src/                  # Source code directory
│   └── hh_mcp_comfyui/
│       ├── comfyui_client.py    # ComfyUI client implementation
│       ├── server.py            # MCP service main file
│       └── workflows/           # Workflow files directory
```


 ### Initialize project development environment:  

  ```bash
  # Clone the repository.
  $ git clone https://github.com/zjf2671/hh-mcp-comfyui.git

  $ cd hh-mcp-comfyui

  # Initialized venv
  $ uv venv

  # Activate the virtual environment.
  $ .venv\Scripts\activate

  # Install dependencies.
  $ uv lock
  Resolved 30 packages in 1ms

  # sync dependencies.
  $ uv sync
  Resolved 30 packages in 2.54s
  Audited 29 package in 0.02ms
  ```

### Check if the service is normal

  ```bash
  $ uv --directory your_local_install_directory/hh-mcp-comfyui run hh-mcp-comfyui

  INFO:__main__:Scanning for workflows in: D:\cygitproject\hh-mcp-comfyui\src\hh_mcp_comfyui\workflows
  INFO:__main__:Registered resource: workflow://t2image_bizyair_flux -> t2image_bizyair_flux.json
  INFO:__main__:Starting ComfyUI MCP Server...
  ```
### Use MCP Inspector to test server tools
  
  ```bash
  $ npx @modelcontextprotocol/inspector uv --directory your_local_install_directory/hh-mcp-comfyui run hh-mcp-comfyui
  ```

### MCP Configuration
  
  ```bash
  {
    "mcpServers": {
      "hh-mcp-comfyui": {
        "command": "uv",
        "args": [
          "--directory",
          "absolute_project_path (e.g.: D:/hh-mcp-comfyui)",
          "run",
          "hh-mcp-comfyui"
        ],
        "env": {
          "COMFYUI_API_BASE": "http://127.0.0.1:8188",
          "COMFYUI_WORKFLOWS_DIR": "/path/hh-mcp-comfyui/workflows"
        }
      }
    }
  }
  ```
## Contribution

1. Fork the project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---
## For questions, contact me via WeChat Official Account:

*<center>![Official Account QR Code](https://image.harryzhang.site/2025/04/image-1-5ac2e62b072e6f1d6eb4e3638634094c.png)</center>*

<center><u>👆 Scan to follow and discover more fun stuff!</u></center>

---
