from flask import json
import modal
import logging
from quart import Quart, request, jsonify
from modal import App, Image, asgi_app
import os
import openai
from openai import OpenAI, OpenAIError, RateLimitError
from dotenv import load_dotenv
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Create a Modal app with the required image
image = Image.debian_slim().pip_install(["quart", "openai", "python-dotenv"])

app = App(
    "loan-officer-integration",
    image=image,
    secrets=[modal.Secret.from_name("OPENAI_API_KEY")]
)

quart_app = Quart(__name__)

# Set the API key from environment variable
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define the endpoint
@quart_app.route('/api/teli_response', methods=['POST'])
async def generate_loan_officer_response():
    try:
        start_time = time.time()
        raw_data = await request.get_data()  # Get the raw request body
        print(f"Raw data: {raw_data.decode('utf-8')}")

        data = json.loads(raw_data.decode('utf-8'))  # Manually load JSON from raw data
        print(f"Received data: {data}")

        if data is None:
          return jsonify({"error": "Empty or invalid JSON body"}), 400

        # Validate required fields
        required_fields = ["first_name", "last_name", "unique_id", "messages"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing or empty field: {field}"}), 400

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        unique_id = data.get("unique_id")
        messages = data.get("messages")

        logger.info(f"Processing request for unique_id: {unique_id[:3]}***")

        if not isinstance(data["unique_id"], (str, int)):
            return jsonify({"error": "unique_id must be a string or integer."}), 400

        if not any(msg["role"] == "customer" for msg in messages):
            return jsonify({"error": "No customer messages found in the conversation history."}), 400


        if not isinstance(data["messages"], list) or not all(
            "role" in msg and "content" in msg for msg in data["messages"]
        ):
            return jsonify({"error": "Invalid messages format"}), 400

        last_customer_message = next(
            (msg["content"] for msg in reversed(messages) if msg["role"] == "customer"),
            None,
        )

        if not last_customer_message:
            return jsonify({"error": "No customer message found in conversation history."}), 400

        # Truncate conversation history to fit within token limits
        truncated_messages = truncate_messages(data["messages"])

        # Formulate the prompt for GPT
        prompt = f"You are a loan officer. Here is the conversation:\n\n" + \
                 "\n".join([f"{msg['role']}: {msg['content']}" for msg in truncated_messages]) + \
                 f"\nCustomer: {last_customer_message}"

        # Call OpenAI API using the new v1 structure
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use the correct model
            messages=[
                {"role": "system", "content": "You are a helpful and professional loan officer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=min(3000 - len(prompt.split()), 150),  # Adjust tokens
            temperature=0.7
        )
        loan_officer_response = response.choices[0].message.content.strip()
        # Optionally add customer name dynamically
        loan_officer_response = f"{first_name}, {loan_officer_response}"

        end_time = time.time()
        logger.info(f"Request processed in {end_time - start_time:.2f} seconds.")

        return jsonify({"content": loan_officer_response}), 200

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return jsonify({"error": "OpenAI API error: " + str(e)}), 500
    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {e}")
        return jsonify({"error": "Rate limit exceeded: " + str(e)}), 429
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


def truncate_messages(messages, max_tokens=3000):
    """
    Truncate or summarize older messages to stay within the token limit.
    """
    truncated = []
    total_tokens = 0
    for msg in reversed(messages):
        # Estimate tokens (simple approximation)
        msg_tokens = len(msg["content"].split())
        if total_tokens + msg_tokens > max_tokens:
            break
        truncated.append(msg)
        total_tokens += msg_tokens
    return list(reversed(truncated))  # Return in original order


# Set up the ASGI app with the Quart app
@app.function()
@asgi_app()
def quart_asgi_app():
    return quart_app

# Run the app in Modal
if __name__ == "__main__":
    quart_app.run(host="0.0.0.0", port=5000, debug=True)




# Set up logging
# logging.basicConfig(level=logging.INFO)
# # Create the app with FastAPI support
# image = modal.Image.debian_slim().pip_install("fastapi[standard]")
# app = modal.App(image=image)

# Define the function to handle the endpoint and expose it as a web endpoint
# @app.function()
# @modal.web_endpoint(method="POST")
# async def generate_loan_officer_response(request):
#     try:
#         logging.info("Inside generate_loan_officer_response function.")

#         # Parse JSON payload from request
#         data = await request.json()

#         logging.info(f"Received data: {data}")

#         first_name = data.get("first_name")
#         last_name = data.get("last_name")
#         unique_id = data.get("unique_id")
#         messages = data.get("messages")

#         # Validate input
#         if not all([first_name, last_name, unique_id, messages]):
#             return modal.web.Response(
#                 status_code=400,
#                 content={"error": "Missing one or more required fields."},
#             )

#         # Get the last customer message and prepare GPT4o input
#         last_customer_message = None
#         for message in reversed(messages):
#             if message["role"] == "customer":
#                 last_customer_message = message["content"]
#                 break

#         if not last_customer_message:
#             return modal.web.Response(
#                 status_code=400,
#                 content={"error": "No customer message found in conversation history."},
#             )

#         # Simulated GPT4o response (replace with actual API call in production)
#         loan_officer_response = f"Thank you for reaching out, {first_name}. Here's how I can assist you with your inquiry..."

#         # Construct response
#         response_content = {
#             "content": loan_officer_response
#         }
#         return modal.web.Response(status_code=200, content=response_content)

#     except Exception as e:
#         return modal.web.Response(
#             status_code=500,
#             content={"error": f"Internal server error: {str(e)}"},
#         )

# # Entrypoint for local testing (if needed)
# if __name__ == "__main__":
#     app.serve()  # Start the app locally with live updates
#     print("Modal app is running locally.")

