import modal
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
# Create the app with FastAPI support
image = modal.Image.debian_slim().pip_install("fastapi[standard]")
app = modal.App(image=image)

# Define the function to handle the endpoint and expose it as a web endpoint
@app.function()
@modal.web_endpoint(method="POST")
async def generate_loan_officer_response(request):
    try:
        logging.info("Inside generate_loan_officer_response function.")

        # Parse JSON payload from request
        data = await request.json()

        logging.info(f"Received data: {data}")

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        unique_id = data.get("unique_id")
        messages = data.get("messages")

        # Validate input
        if not all([first_name, last_name, unique_id, messages]):
            return modal.web.Response(
                status_code=400,
                content={"error": "Missing one or more required fields."},
            )

        # Get the last customer message and prepare GPT4o input
        last_customer_message = None
        for message in reversed(messages):
            if message["role"] == "customer":
                last_customer_message = message["content"]
                break

        if not last_customer_message:
            return modal.web.Response(
                status_code=400,
                content={"error": "No customer message found in conversation history."},
            )

        # Simulated GPT4o response (replace with actual API call in production)
        loan_officer_response = f"Thank you for reaching out, {first_name}. Here's how I can assist you with your inquiry..."

        # Construct response
        response_content = {
            "content": loan_officer_response
        }
        return modal.web.Response(status_code=200, content=response_content)

    except Exception as e:
        return modal.web.Response(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"},
        )

# Entrypoint for local testing (if needed)
if __name__ == "__main__":
    app.serve()  # Start the app locally with live updates
    print("Modal app is running locally.")

