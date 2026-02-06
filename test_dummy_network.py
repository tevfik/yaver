# Network utilities placeholder
import requests


def checks_google():
    """
    Checks if google.com is reachable via requests.

    Returns:
        bool: True if google.com is reachable, False otherwise.
    """
    try:
        response = requests.get("https://google.com")
        if response.status_code == 200:
            return True
        else:
            raise Exception("Failed to reach Google")
    except Exception as e:
        print(f"Error checking Google: {e}")
        return False
