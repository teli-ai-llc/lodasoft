from flask import json
import modal
import logging
from quart import Quart, request, jsonify
from modal import App, Image, asgi_app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a Modal app with the required image
image = Image.debian_slim().pip_install("quart")
app = App("loan-officer-integration", image=image)

# Initialize Quart app
quart_app = Quart(__name__)

# Define the endpoint
@quart_app.route('/api/teli_response', methods=['POST'])
async def generate_loan_officer_response():
    try:
        raw_data = await request.get_data()  # Get the raw request body
        print(f"Raw data: {raw_data.decode('utf-8')}")

        data = json.loads(raw_data.decode('utf-8'))  # Manually load JSON from raw data
        print(f"Received data: {data}")  # Check what
        # data = await request.get_json()
        # print(f"Received data: {data}")  # or use logging.debug if needed

        # if data is None:
        #   return jsonify({"error": "Empty or invalid JSON body"}), 400

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        unique_id = data.get("unique_id")
        messages = data.get("messages")

        if not all([first_name, last_name, unique_id, messages]):
            return jsonify({"error": "Missing required fields"}), 400

        last_customer_message = next(
            (msg["content"] for msg in reversed(messages) if msg["role"] == "customer"),
            None,
        )

        if not last_customer_message:
            return jsonify({"error": "No customer message found in conversation history."}), 400

        loan_officer_response = f"Thank you for reaching out, {first_name}. Here's how I can assist."
        return jsonify({"content": loan_officer_response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

