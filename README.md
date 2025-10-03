# OpenBB Documentation MCP Server

A Model Context Protocol (MCP) server that exposes OpenBB Workspace documentation as structured, callable tools. This enables AI assistants and LLMs to easily access and search through OpenBB's comprehensive documentation.

## Features

- **Section Discovery**: Browse and search through available documentation sections from the OpenBB table of contents
- **Content Retrieval**: Fetch detailed documentation content for specific sections
- **Intelligent Search**: Filter documentation sections by query terms
- **Structured Output**: Returns well-formatted JSON data for easy consumption by AI systems

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd openbb-docs-mcp-server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Note: This project requires Python 3.11+ and uses FastMCP 2.0+.

## Usage

### Running the Server

#### Stdio Transport (for local MCP clients):
```bash
fastmcp run server.py
```

#### HTTP Transport (for remote access):
```bash
fastmcp run server.py --transport http --port 8000
```

#### Using Python directly (with uvicorn and CORS):
```bash
python3.11 server.py
```

The server will start on port 8014 by default, or you can set a custom port:
```bash
PORT=9000 python3.11 server.py
```

### Available Tools

#### 1. `discover_openbb_sections`

Discovers available OpenBB documentation sections from the table of contents.

**Parameters:**
- `query` (optional): Search query to filter relevant sections

**Returns:**
- `success`: Boolean indicating operation success
- `sections`: Array of section objects with title, category, URL, and description
- `total_sections`: Total number of sections found
- `query_used`: The search query that was applied (if any)

**Example:**
```json
{
  "success": true,
  "sections": [
    {
      "title": "Copilot Basics",
      "category": "AI Features",
      "url": "https://docs.openbb.co/workspace/analysts/ai-features/copilot-basics",
      "description": "AI Features: Copilot Basics"
    }
  ],
  "total_sections": 75,
  "query_used": null
}
```

#### 2. `fetch_openbb_content`

Fetches specific documentation content from OpenBB docs based on section titles.

**Parameters:**
- `section_titles`: Array of section titles to fetch content for
- `max_sections` (optional): Maximum number of sections to fetch (default: 3)

**Returns:**
- `success`: Boolean indicating operation success
- `content`: Object mapping section titles to their content
- `sections_found`: Number of sections successfully retrieved
- `sections_requested`: Number of sections that were requested
- `truncated`: Boolean indicating if the request was limited by max_sections

**Example:**
```json
{
  "success": true,
  "content": {
    "Copilot Basics": "title: Copilot Basics\\nsidebar_position: 7\\n..."
  },
  "sections_found": 1,
  "sections_requested": 1,
  "truncated": false
}
```

## Architecture

The MCP server consists of:

1. **TOC Parser**: Fetches and parses the OpenBB documentation table of contents from `https://docs.openbb.co/workspace/llms.txt`
2. **Content Fetcher**: Retrieves full documentation content from `https://docs.openbb.co/workspace/llms-full.txt`
3. **Section Matcher**: Intelligently matches section titles between the TOC and full content
4. **FastMCP Integration**: Exposes functionality through the Model Context Protocol

## Configuration

The server can be configured using `fastmcp.json`:

```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "type": "filesystem",
    "path": "server.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "type": "uv",
    "python": ">=3.10",
    "dependencies": ["fastmcp>=2.0.0", "httpx>=0.25.0"]
  },
  "deployment": {
    "transport": "stdio",
    "log_level": "INFO"
  }
}
```

## Testing

Run the test suite to verify server functionality:

```bash
python3.11 test_server.py
```

The test script will:
1. Test section discovery functionality
2. Test content fetching with AI-related sections
3. Test search functionality with query filters

## Examples

### Basic Usage with FastMCP Client

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("server.py") as client:
        # Discover all sections
        result = await client.call_tool("discover_openbb_sections")
        sections = result.data['sections']

        # Search for specific content
        search_result = await client.call_tool(
            "discover_openbb_sections",
            {"query": "copilot"}
        )

        # Fetch content for specific sections
        content = await client.call_tool(
            "fetch_openbb_content",
            {"section_titles": ["Copilot Basics"], "max_sections": 1}
        )
        print(content.data)

asyncio.run(main())
```

### Integration with Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "openbb-docs": {
      "command": "fastmcp",
      "args": ["run", "/path/to/openbb-docs-mcp-server/server.py"]
    }
  }
}
```

## Dependencies

- `fastmcp>=2.0.0`: FastMCP framework for building MCP servers
- `httpx>=0.25.0`: HTTP client for fetching documentation
- `starlette>=0.27.0`: ASGI framework for web applications
- `uvicorn>=0.30.0`: ASGI server for running the application
- `typing-extensions>=4.0.0`: Type hints support

## CORS Configuration

The server includes CORS middleware configured for MCP session management:
- Exposes `mcp-session-id` and `mcp-protocol-version` headers
- Allows all origins (configure more restrictively in production)
- Supports credentials and common HTTP methods

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and support, please create an issue in the repository or contact the development team.