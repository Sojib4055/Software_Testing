import os
import openai
import pytesseract
from PIL import Image
import cv2
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
from kivy.config import Config
from loguru import logger
from datetime import datetime

# Configure Kivy window size
Config.set("graphics", "width", "800")
Config.set("graphics", "height", "600")

# Configure OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configure Tesseract OCR path
pytesseract.pytesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

class TestApp(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"

        # Instruction label
        self.label = Label(
            text="Upload a GUI Image or Enter a URL for Test Case Generation",
            size_hint=(1, 0.1)
        )
        self.add_widget(self.label)

        # Text input for URL
        self.url_input = TextInput(
            hint_text="Enter URL here",
            multiline=False,
            size_hint=(1, 0.1)
        )
        self.add_widget(self.url_input)

        # File chooser to select images
        self.file_chooser = FileChooserListView(
            path=os.path.expanduser("~"),
            filters=["*.png", "*.jpg", "*.jpeg"],
            filter_dirs=False,
            size_hint=(1, 0.6)
        )
        self.add_widget(self.file_chooser)

        # Button to trigger test case generation
        self.upload_button = Button(
            text="Generate Test Cases",
            size_hint=(1, 0.2)
        )
        self.upload_button.bind(on_press=self.generate_test_cases)
        self.add_widget(self.upload_button)

        # Selenium WebDriver setup
        self.driver = None
        self.init_webdriver()

    def init_webdriver(self):
        """Initialize Selenium WebDriver using WebDriver Manager."""
        try:
            options = Options()
            options.add_argument("--headless")  # Optional headless mode
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")

            # Automatically download and manage ChromeDriver
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            logger.info("WebDriver initialized successfully.")
        except Exception as e:
            self.driver = None
            logger.error(f"Failed to initialize WebDriver: {e}")

    def generate_test_cases(self, instance):
        selected_file = self.file_chooser.selection
        url = self.url_input.text.strip()

        if url:
            try:
                logger.info(f"Processing URL: {url}")
                selenium_description = self.extract_login_related_elements(url)

                if selenium_description:
                    # Save test cases to Excel
                    output_file = os.path.expanduser(f"~/url_test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
                    self.save_test_cases_to_excel(selenium_description, output_file)
                    self.label.text = "Test Cases Generated and Saved Successfully for URL!"
                    logger.info("Test cases saved to Excel.")
                else:
                    self.label.text = "No clickable elements found on the page."
                    logger.warning("No clickable elements found.")

            except Exception as e:
                self.label.text = f"Error: {str(e)}"
                logger.error(f"Unexpected error for URL: {e}")

        elif selected_file:
            file_path = selected_file[0]
            try:
                logger.info(f"Selected file: {file_path}")

                # Step 1: Process the image using OpenCV for visual element detection
                img = cv2.imread(file_path)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

                # Detect contours (representing GUI elements)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                visual_elements = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w > 50 and h > 20:  # Filter small noise
                        visual_elements.append((x, y, w, h))

                extracted_text = pytesseract.image_to_string(Image.open(file_path))

                visual_description = "\n".join([
                    f"Element at (x: {x}, y: {y}, width: {w}, height: {h})"
                    for x, y, w, h in visual_elements
                ])

                combined_description = (
                    f"Extracted Text:\n{extracted_text}\n\n"
                    f"Detected Visual Elements:\n{visual_description}"
                )

                self.save_test_cases_to_excel([combined_description], file_path)

            except Exception as e:
                logger.error(f"Unexpected error for file: {e}")

    def save_test_cases_to_excel(self, test_cases, file_path):
        try:
            df = pd.DataFrame(test_cases)
            output_file = os.path.splitext(file_path)[0] + "_test_cases.xlsx"
            df.to_excel(output_file, index=False, engine="openpyxl")
            logger.info(f"Test cases saved to {output_file}.")
        except Exception as e:
            logger.error(f"Failed to save test cases to Excel: {e}")

    def extract_login_related_elements(self, url):
        try:
            self.driver.get(url)
            elements = self.driver.find_elements(By.CSS_SELECTOR, "input, button, a")

            test_cases = []
            for element in elements:
                try:
                    if element.is_displayed():
                        test_cases.append({
                            "Test Case ID": f"TC_{element.tag_name}_{element.get_attribute('id')}",
                            "Test Case Description": f"Test {element.tag_name} element with label '{element.text}'",
                            "Precondition": "Application is running",
                            "Test Steps": f"Interact with {element.tag_name} element",
                            "Expected Result": f"{element.tag_name.capitalize()} element works as expected"
                        })
                except StaleElementReferenceException:
                    continue

            return test_cases
        except Exception as e:
            logger.error(f"Error extracting elements: {e}")
            return []

class MyApp(App):
    def build(self):
        return TestApp()

if __name__ == "__main__":
    MyApp().run()
