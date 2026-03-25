import time
import random
from anthropic import _exceptions

def api_call_with_retry(func, *args, max_retries=5, base_delay=10, **kwargs):
    """
    Wraps any Anthropic API call with exponential backoff retry logic.
    Handles 529 Overloaded and 529 RateLimitError gracefully.
    
    Usage:
        response = api_call_with_retry(client.messages.create, model=..., ...)
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)

        except _exceptions.OverloadedError as e:
            if attempt == max_retries:
                print(f"\n[RETRY] Max retries reached. Giving up.")
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 2)
            print(f"\n[RETRY] API overloaded (529). Attempt {attempt}/{max_retries}. Waiting {delay:.1f}s...")
            time.sleep(delay)

        except _exceptions.RateLimitError as e:
            if attempt == max_retries:
                print(f"\n[RETRY] Rate limit max retries reached. Giving up.")
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 2)
            print(f"\n[RETRY] Rate limited. Attempt {attempt}/{max_retries}. Waiting {delay:.1f}s...")
            time.sleep(delay)

        except _exceptions.APIStatusError as e:
            # Only retry on 5xx server errors
            if e.status_code >= 500:
                if attempt == max_retries:
                    raise
                delay = base_delay * (2 ** (attempt - 1))
                print(f"\n[RETRY] Server error {e.status_code}. Attempt {attempt}/{max_retries}. Waiting {delay:.1f}s...")
                time.sleep(delay)
            else:
                # 4xx errors are not retryable
                raise
