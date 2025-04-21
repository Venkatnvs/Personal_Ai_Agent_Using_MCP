import logging
import wikipedia
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Wikipedia Tool")

@dataclass
class WikipediaInput:
    """
    Provide a Wikipedia action and query to retrieve information.
    
    Actions:
    - 'summary': Get a brief summary (3 sentences)
    - 'full_article': Get full content of the article
    - 'search': Search for related topics
    """
    action: str  # 'summary', 'full_article', or 'search'
    query: str   # e.g., 'Artificial Intelligence'

@mcp.tool()
def wikipedia_tool(input_data: WikipediaInput) -> dict:
    """
    Fetches information from Wikipedia based on the specified action.
    Supports summary retrieval, full article fetch, and topic search.
    """

    action = input_data.action.lower()
    query = input_data.query.strip()

    if not query:
        error_msg = "Parameter 'query' is required."
        logging.error(error_msg)
        return {"status": "error", "message": error_msg}

    try:
        if action == "summary":
            summary = wikipedia.summary(query, sentences=3)
            return {
                "status": "success",
                "message": "Wikipedia summary retrieved.",
                "title": query,
                "summary": summary
            }

        elif action == "full_article":
            page = wikipedia.page(query)
            return {
                "status": "success",
                "message": "Wikipedia full article retrieved.",
                "title": page.title,
                "content": page.content
            }

        elif action == "search":
            search_results = wikipedia.search(query, results=5)
            if not search_results:
                return {"status": "error", "message": f"No Wikipedia search results for '{query}'."}
            return {
                "status": "success",
                "message": "Wikipedia search results retrieved.",
                "results": search_results
            }

        else:
            error_msg = "Invalid action. Use 'summary', 'full_article', or 'search'."
            logging.error(error_msg)
            return {"status": "error", "message": error_msg}

    except wikipedia.exceptions.PageError:
        return {"status": "error", "message": f"No Wikipedia page found for '{query}'."}

    except wikipedia.exceptions.DisambiguationError as e:
        return {
            "status": "error",
            "message": f"Query '{query}' is ambiguous. Suggestions: {', '.join(e.options[:5])}"
        }

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return {"status": "error", "message": "An unexpected error occurred."}

if __name__ == "__main__":
    mcp.run(transport="stdio")
