"""
HKU Portal Authentication Verification
only for verifying HKU Portal email and password validity
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


def verify_hku_credentials(email, password, headless=True, verbose=False):
    """
    verify HKU Portal email and password validity

    Args:
        email (str): HKU email address (e.g., u123456@connect.hku.hk)
        password (str): Password
        headless (bool): Whether to run the browser in headless mode
        verbose (bool): Whether to print detailed logs

    Returns:
        dict: Verification result
            - success (bool): Whether the verification was successful
            - message (str): Result message
            - error_type (str): Error type (if failed) - 'invalid_email', 'invalid_password', 'network_error', 'unknown'
    """

    def _log(message):
        """Internal logging function"""
        if verbose:
            print(f"[AUTH] {message}")

    driver = None

    try:
        # Validate email format
        if "@" not in email or "hku" not in email.lower():
            return {
                "success": False,
                "message": "Please enter a valid HKU email address",
                "error_type": "invalid_email",
            }

        # Set Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--disable-css")
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.stylesheets": 2
        })
        chrome_options.add_argument("--fast")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-plugin-types=all")
        chrome_options.add_argument("--disable-http2")
        chrome_options.add_argument("--disable-prefetching")
        chrome_options.add_argument("--disable-preconnect")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--disable-dom-distiller")

        # Initialize WebDriver
        _log("Initializing browser...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Access HKU Portal login page
        _log("Accessing HKU Portal login page...")
        driver.get("https://moodle.hku.hk/login/index.php?authCAS=CAS")
        time.sleep(0.5)

        # Step 1: Enter email
        _log("Entering email...")
        try:
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_input.clear()
            email_input.send_keys(email)
            time.sleep(0.5)

            # Click LOG IN button
            login_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "login_btn"))
            )
            login_button.click()
            _log("Clicked LOG IN button, waiting for password page...")
            time.sleep(0.5)

        except TimeoutException:
            return {
                "success": False,
                "message": "Unable to load login page, please check your network connection",
                "error_type": "network_error",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error occurred while entering email: {str(e)}",
                "error_type": "unknown",
            }

        # Step 2: Enter password
        _log("Entering password...")
        try:
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "passwordInput"))
            )
            password_input.clear()
            password_input.send_keys(password)
            _log("Entered password")
            time.sleep(0.5)

            # Click login button
            submit_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "submitButton"))
            )
            submit_button.click()
            _log("Clicked login button, waiting for verification result...")
            time.sleep(1.5)

        except TimeoutException:
            return {
                "success": False,
                "message": "Unable to load password input page",
                "error_type": "network_error",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error occurred while entering password: {str(e)}",
                "error_type": "unknown",
            }

        # Step 3: Check for error messages (e.g., from Figure 1)
        _log("Checking login result...")
        try:
            # First, check if "Stay signed in" page appears (indicates successful login)
            try:
                _log("Checking for 'Stay signed in' page...")
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.ID, "idSIButton9"))
                )
                _log("Detected 'Stay signed in' page, verification successful!")
                return {
                    "success": True,
                    "message": "Email and password verification successful",
                    "error_type": None,
                }
            except TimeoutException:
                _log(
                    "'Stay signed in' page not detected, checking for errors or redirect..."
                )

            # Check current URL
            current_url = driver.current_url
            _log(f"Current URL: {current_url}")

            # Check if already redirected to Moodle page
            if "moodle.hku.hk" in current_url and "login" not in current_url.lower():
                _log("Successfully redirected to Moodle, verification successful!")
                return {
                    "success": True,
                    "message": "Email and password verification successful",
                    "error_type": None,
                }

            # Check for error message elements
            _log("Checking for error messages...")
            error_selectors = [
                (By.ID, "errorText"),
                (By.ID, "error"),
                (By.CLASS_NAME, "error"),
                (By.CLASS_NAME, "alert-error"),
                (
                    By.XPATH,
                    "//*[contains(@class, 'error') and contains(@class, 'alert')]",
                ),
                (By.XPATH, "//*[@id='errorText']"),
                (By.XPATH, "//*[contains(text(), '用户名或密码不正确')]"),
                (By.XPATH, "//*[contains(text(), 'incorrect')]"),
                (By.XPATH, "//*[contains(text(), 'Invalid')]"),
            ]

            for selector_type, selector_value in error_selectors:
                try:
                    error_element = driver.find_element(selector_type, selector_value)
                    if error_element and error_element.is_displayed():
                        error_text = error_element.text.strip()
                        _log(f"Found error message: {error_text}")
                        return {
                            "success": False,
                            "message": f"Username or password is incorrect: {error_text}",
                            "error_type": "invalid_password",
                        }
                except:
                    continue

            # If still on login.microsoftonline.com and no "Stay signed in" page found
            if "login.microsoftonline.com" in current_url:
                _log("Still on Microsoft login page, likely password error")
                return {
                    "success": False,
                    "message": "Username or password is incorrect",
                    "error_type": "invalid_password",
                }

            # Unable to determine result
            _log(f"Unable to determine verification result, current URL: {current_url}")
            return {
                "success": False,
                "message": "Unable to determine verification result, possible network issue",
                "error_type": "network_error",
            }

        except Exception as e:
            _log(f"Error occurred while checking result: {str(e)}")
            return {
                "success": False,
                "message": f"Error occurred while checking result: {str(e)}",
                "error_type": "unknown",
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error occurred while checking result: {str(e)}",
            "error_type": "unknown",
        }

    finally:
        # Close the browser
        if driver:
            try:
                _log("Closing browser...")
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    # Test example
    print("HKU Portal Authentication Test")
    print("=" * 50)

    # Get email and password from user input
    test_email = "your hku email"
    test_password = "your hku password"

    print("\nStarting verification...")
    result = verify_hku_credentials(
        test_email, test_password, headless=True, verbose=True
    )

    print("\n" + "=" * 50)
    print("Verification Result:")
    print(result)
    print("=" * 50)
