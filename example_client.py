import asyncio
import httpx
import json

async def main():
    """
    An example client to interact with the USASpending MCP Server.
    """
    server_url = "http://127.0.0.1:3002/"

    # Get search parameters from user
    keyword = input("Enter search keyword (e.g., 'space', 'dell', 'construction'): ").strip()
    if not keyword:
        print("Keyword is required. Using 'space' as default.")
        keyword = "space"
    
    try:
        limit = int(input("Enter number of results to show (default 3): ").strip() or "3")
    except ValueError:
        print("Invalid number. Using default limit of 3.")
        limit = 3
    
    # Build the payload that the MCP server expects
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_use",
                        "tool_name": "search_federal_awards",
                        "tool_arguments": {
                            "query": keyword,
                            "max_results": limit
                        }
                    }
                ]
            }
        ]
    }

    print("Sending request to the MCP server...")
    print(json.dumps(payload, indent=2))

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(server_url, json=payload)
            response.raise_for_status()  # Raise an exception for bad status codes

            print("\nReceived response from the server:")
            
            # The server responds with a response array containing content blocks
            response_data = response.json()
            if isinstance(response_data, str):
                print(response_data)
            elif isinstance(response_data, list):
                for content in response_data:
                    if isinstance(content, dict) and content.get("type") == "text":
                        print(content["text"])
                    else:
                        print(json.dumps(content, indent=2))
            else:
                print("Received an unexpected response:")
                print(json.dumps(response_data, indent=2))

    except httpx.RequestError as e:
        print(f"\nAn error occurred while requesting {e.request.url!r}.")
        print("Please ensure the MCP server is running in another terminal.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    try:
        # Run the main function with asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting client...")
    except Exception as e:
        # Handle any other unexpected errors
        print(f"\nAn unexpected error occurred: {e}")
        raise
