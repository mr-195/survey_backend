from index import app  # Import FastAPI app
from mangum import Mangum  # AWS Lambda adapter

handler = Mangum(app)  # Wrap FastAPI app