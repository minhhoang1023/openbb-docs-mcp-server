"""
OpenBB Documentation MCP Server

This server exposes OpenBB documentation as structured, callable tools through the Model Context Protocol.
It provides two main functionalities:
1. Discovering available documentation sections from the table of contents
2. Fetching specific documentation content from the full docs file
"""

import os
import re
from typing import List, Dict, Any, Optional
import httpx
import uvicorn
from fastmcp import FastMCP
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastMCP server
mcp = FastMCP(
    name="OpenBB Docs Server",
    instructions="""
    This server provides access to OpenBB Workspace documentation.
    Use 'discover_openbb_sections' to find available documentation sections,
    then use 'fetch_openbb_content' to retrieve specific section content.
    """
)

# Get the Starlette app and add CORS middleware
# Use http_app() with 'http' transport (recommended for production)
app = mcp.http_app()

origins = [
    "https://pro.openbb.co",
    "https://pro.openbb.dev",
    "http://localhost:1420"
]

# Add CORS middleware with proper header exposure for MCP session management
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Configure this more restrictively in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id", "mcp-protocol-version"],  # Allow client to read session ID
    max_age=86400,
)

# URLs for OpenBB documentation
TOC_URL = "https://docs.openbb.co/workspace/llms.txt"
FULL_DOCS_URL = "https://docs.openbb.co/workspace/llms-full.txt"


@mcp.tool()
async def identify_openbb_docs_sections(user_query: str) -> Dict[str, Any]:
    """
    Identify the most relevant OpenBB documentation sections based on a user's query.

    This tool provides the COMPLETE table of contents from OpenBB documentation and expects
    the LLM to analyze it intelligently to select the most relevant sections.

    ANALYSIS INSTRUCTIONS FOR THE LLM:
    1. **Carefully read** both the title AND description of each section. Titles give primary signals.
    Descriptions clarify scope (setup vs. concept vs. workflow vs. integration).
    2. **Understand intent**: Match the semantic meaning of the user's query, not just keywords
    3. **Evaluate relevance**: Consider which sections would most likely contain the information needed
    4. **Prioritize quality**: Only select sections that are truly relevant to the query
    5. **Rank by relevance**: Return up to 3 sections, ordered from most to least relevant
    6. **Be selective**: If no sections are genuinely relevant, return an empty list - do NOT force matches

    SELECTION CRITERIA:
    - Does the section title/description directly address the user's question?
    - Would this section likely contain detailed information about the query topic?
    - Is this section more relevant than other available options?
    - Consider both exact matches AND semantically related topics

    OUTPUT REQUIREMENTS:
    - Return a list of up to 3 section titles
    - Maximum 3 sections (can be 0, 1, 2, or 3)
    - Must be ranked by relevance (most relevant first)
    - Return empty if truly no relevant sections exist

    Args:
        user_query: The user's question or information request
    """
    return await _identify_sections_async(user_query)


@mcp.tool()
async def fetch_openbb_content(section_titles: List[str], user_query: str) -> Dict[str, Any]:
    """
    Fetch specific documentation content from OpenBB docs based on section titles.

    You MUST call 'identify_openbb_docs_sections' first to obtain the exact section titles
    before calling this tool. Use the section titles identified from that process.

    Workflow:
    1. Call 'identify_openbb_docs_sections' with the user's query
    2. The LLM analyzes the raw TOC and identifies up to 3 relevant section titles
    3. Pass those exact section titles AND the original user query to this function
    4. Use the returned content to answer the user's question

    Args:
        section_titles: List of exact section titles identified from 'identify_openbb_docs_sections'
        user_query: The original user's question/query
    """
    return await _fetch_content_async(section_titles, user_query)


async def _identify_sections_async(user_query: str) -> Dict[str, Any]:
    """
    Async implementation for identifying relevant sections.
    Returns the raw TOC content for LLM to analyze and select relevant sections.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(TOC_URL)
            response.raise_for_status()
            toc_content = response.text

        return {
            "success": True,
            "query": user_query,
            "raw_toc_content": toc_content,
            "instruction": """

    This tool provides the COMPLETE table of contents from OpenBB documentation and expects
    the LLM to analyze it intelligently to identify the most relevant OpenBB documentation sections based on a user's query
    and return a list of up to 3 section titles.

    SELECTION GUIDELINES:
    1. **Carefully read** both the title AND description of each section. Titles give primary signals.
    Descriptions clarify scope (setup vs. concept vs. workflow vs. integration).
    2. **Understand intent**: Match the semantic meaning of the user's query, not just keywords
    3. **Evaluate relevance**: Consider which sections would most likely contain the information needed
    4. **Prioritize quality**: Only select sections that are truly relevant to the query
    5. **Rank by relevance**: Return up to 3 sections, ordered from most to least relevant
    6. **Be selective**: If no sections are genuinely relevant, return an empty list - do NOT force matches

    SELECTION CRITERIA:
    - Does the section title/description directly address the user's question?
    - Would this section likely contain detailed information about the query topic?
    - Is this section more relevant than other available options?
    - Consider both exact matches AND semantically related topics

    OUTPUT REQUIREMENTS:
    - Return a list of up to 3 section titles
    - Maximum 3 sections (can be 0, 1, 2, or 3)
    - Must be ranked by relevance (most relevant first)
    - Return empty if truly no relevant sections exist

    CITATION FORMAT (for OpenBB Copilot compatibility):
    If there are relevant section, make sure to include all documentation URLs in the following format:

        answer="Your answer text here",
        citations=[
            Citation(
                source_info=SourceInfo(type="web", name=url),
                details=[{"Website": url}]
            )

    Key citation structure:
    - Return a result object with answer (str) and citations (list[Citation])
    - Each Citation needs source_info and details
    - For URLs: source_info=SourceInfo(type="web", name=url) and details=[{"Website": url}]
"""
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": user_query,
            "raw_toc_content": ""
        }


async def _fetch_content_async(section_titles: List[str], user_query: str) -> Dict[str, Any]:
    """
    Fetch full documentation and extract only the relevant sections.
    Returns extracted content with the original user query and instructions for the LLM.
    """
    try:
        # Fetch the entire full documentation
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(FULL_DOCS_URL)
            response.raise_for_status()
            full_docs = response.text

        # Extract only the relevant sections from the full docs
        # This prevents sending the entire docs which would exceed context limits
        content_sections = _extract_sections_from_docs(full_docs, section_titles)

        return {
            "success": True,
            "user_query": user_query,
            "extracted_content": content_sections,
            "sections_found": len(content_sections),
            "instruction": """
User's question: {query}

The relevant documentation sections have been extracted above in 'extracted_content'.

RESPONSE GUIDELINES:
1. **Stay grounded**: Use only facts present in extracted_content. No speculation or unstated assumptions.
2. **Synthesize across sections**: If the answer spans multiple sections, merge them coherently. Prefer the most specific, actionable details.
3. **Cite precisely**:
   - After each factual claim or step, cite the section with the shortest sufficient reference in square brackets, e.g., [Copilot Basics], [Data Handling]
   - When a claim depends on multiple sections, include up to two citations, e.g.,
   Make sure to follow this format or OpenBB Copilot compatibility:
    If there are relevant section, make sure to include all documentation URLs in the following format:
        answer="Your answer text here",
        citations=[
            Citation(
                source_info=SourceInfo(type="web", name=url),
                details=[{"Website": url}]
            )
   [MCP Tools; Orchestrator Mode]
   - Keep citations lightweight—do not include URLs unless explicitly present and relevant
4. **Be exact**: Preserve terminology, parameter names, and constraints exactly as shown. If docs present syntax, show it verbatim in a code block.
5. **Respect scope**: If extracted_content does not contain the needed information, state this plainly and direct the user to support@openbb.co
6. **Multilingual**: Respond in the same language as the user query where possible
7. **No chain-of-thought**: Provide conclusions and steps, not internal reasoning

OUTPUT STYLE:
- Direct and actionable. Use clear steps for how-to, compact explanation for concepts
- Use code blocks for commands/code snippets (specify language when obvious)
- Use short bullet lists for options/parameters
- Use tables only when they improve clarity
- Citations at the end of relevant sentence/step (not grouped at the end)
- No extra boilerplate (don't restate the prompt or list all sections)
""".format(query=user_query)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "user_query": user_query,
            "extracted_content": {}
        }


def _parse_toc(toc_content: str, query: Optional[str] = None) -> List[Dict[str, str]]:
    """Parse the table of contents and extract section information."""
    sections = []
    lines = toc_content.strip().split('\n')

    current_category = ""

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Detect category headers (lines that don't start with - or *)
        if not line.startswith(('-', '*', '1.', '2.', '3.', '4.', '5.')):
            # Check if it's a main section header
            if line and not line.startswith('#') and not line.startswith('http'):
                current_category = line.replace('#', '').strip()
            continue

        # Extract markdown links
        link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
        if link_match:
            title = link_match.group(1).strip()
            url = link_match.group(2).strip()

            # Filter by query if provided
            if query and query.lower() not in title.lower() and query.lower() not in current_category.lower():
                continue

            sections.append({
                "title": title,
                "category": current_category,
                "url": url,
                "description": f"{current_category}: {title}" if current_category else title
            })

    return sections


def _extract_sections_from_docs(full_docs: str, section_titles: List[str]) -> Dict[str, str]:
    """Extract specific sections from the full documentation."""
    content_sections = {}

    for title in section_titles:
        # Try different matching strategies
        section_content = _find_section_content(full_docs, title)
        if section_content:
            content_sections[title] = section_content
        else:
            content_sections[title] = f"Section '{title}' not found in documentation."

    return content_sections


def _find_section_content(full_docs: str, title: str) -> Optional[str]:
    """Find content for a specific section title in the full docs."""
    lines = full_docs.split('\n')

    # Try to find the section by matching title patterns
    patterns_to_try = [
        f"# {title}",           # Direct header match
        f"## {title}",          # Subheader match
        f"### {title}",         # Sub-subheader match
        title,                  # Direct title match
        title.lower(),          # Lowercase match
        title.replace(' ', '-').lower()  # Slug format
    ]

    for pattern in patterns_to_try:
        for i, line in enumerate(lines):
            if pattern in line.lower() or line.lower().strip() == pattern:
                # Found the section start, now extract content
                content_lines = [line]  # Include the header

                # Extract content until next section or end
                j = i + 1
                while j < len(lines):
                    current_line = lines[j].strip()

                    # Stop if we hit another major section header
                    if (current_line.startswith('# ') or
                        current_line.startswith('## ') and
                        current_line != line.strip()):
                        break

                    content_lines.append(lines[j])
                    j += 1

                    # Limit content length to prevent overwhelming responses
                    if len(content_lines) > 100:
                        content_lines.append("... (content truncated)")
                        break

                return '\n'.join(content_lines)

    return None


if __name__ == "__main__":
    # Use PORT environment variable
    port = int(os.environ.get("PORT", 8000))

    print("Starting FastMCP OpenBB Docs server...")
    print(f"MCP server will be available at: http://localhost:{port}/mcp")
    print("Tools available: discover_openbb_sections, fetch_openbb_content")

    # Run the MCP server with HTTP transport using uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all interfaces for containerized deployment
        port=port,
        log_level="debug"
    )