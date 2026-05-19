import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class RobotClient:
    """
    Singleton class to manage all communication with the Virtual Robot API.
    Ensures we reuse the same HTTP session for efficiency and prevents memory leaks.
    """
    _instance = None

    def __new__(cls):
     
        if cls._instance is None:
            cls._instance = super(RobotClient, cls).__new__(cls)
            cls._instance.base_url = "http://localhost:5000/api"
            # Create a persistent connection pool
            cls._instance.client = httpx.AsyncClient(base_url=cls._instance.base_url)
        return cls._instance

    #  retry up to 3 times if the connection drops
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def get_status(self):
        """Fetches the current status, handling random 503 dropouts gracefully."""
        response = await self.client.get("/status")
        
        # raise_for_status() triggers the Tenacity @retry if it gets a 503 error
        response.raise_for_status() 
        return response.json()

    # ROBUSTNESS: Apply the same retry logic to movement commands
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def move_robot(self, x: int, y: int):
        """Sends a movement command to the robot."""
        payload = {"x": x, "y": y}
        response = await self.client.post("/move", json=payload)
        
        # Raise an error if the robot is busy or offline, triggering the retry
        response.raise_for_status()
        return response.json()