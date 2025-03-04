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
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
from kivy.config import Config
from loguru import logger

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
        """Initialize Selenium WebDriver."""
        try:
            options = Options()
            options.add_argument("--headless")  # Run in headless mode
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            service = Service("path_to_chromedriver")  # Replace with your ChromeDriver path
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("WebDriver initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")

    def generate_test_cases(self, instance):
        selected_file = self.file_chooser.selection
        url = self.url_input.text.strip()

        if url:
            try:
                logger.info(f"Processing URL: {url}")
                selenium_description = self.extract_with_selenium(url)

                # Use OpenAI to generate test cases from Selenium description
                test_cases = self.generate_openai_test_cases(selenium_description)

                # Save test cases to Excel
                output_file = os.path.expanduser(f"~/url_test_cases.xlsx")
                self.save_test_cases_to_excel(test_cases, output_file)

                # Display success message
                self.label.text = "Test Cases Generated and Saved Successfully for URL!"
                logger.info("Test cases saved to Excel.")

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

                # Step 2: Extract text using Tesseract OCR
                extracted_text = pytesseract.image_to_string(Image.open(file_path))

                if not extracted_text.strip() and not visual_elements:
                    logger.warning("No text or visual elements detected in the image.")
                    extracted_text = "No text or visual elements found."

                # Step 3: Combine text and visual element information
                visual_description = "\n".join([
                    f"Element at (x: {x}, y: {y}, width: {w}, height: {h})"
                    for x, y, w, h in visual_elements
                ])

                combined_description = (
                    f"Extracted Text:\n{extracted_text}\n\n"
                    f"Detected Visual Elements:\n{visual_description}"
                )

                # Step 4: Use OpenAI to generate test cases
                test_cases = self.generate_openai_test_cases(combined_description)

                # Step 5: Save test cases to Excel
                self.save_test_cases_to_excel(test_cases, file_path)

                # Display success message
                self.label.text = "Test Cases Generated and Saved Successfully for File!"
                logger.info("Test cases saved to Excel.")

            except Exception as e:
                self.label.text = f"Error: {str(e)}"
                logger.error(f"Unexpected error for file: {e}")
        else:
            self.label.text = "No file or URL provided. Please upload an image or enter a URL."
            logger.warning("No file or URL provided.")

    def extract_with_selenium(self, url):
        """Extract GUI elements and text from a webpage using Selenium."""
        try:
            self.driver.get(url)
            elements = self.driver.find_elements(By.CSS_SELECTOR, "*")

            selenium_elements = []
            for element in elements:
                if element.is_displayed():
                    tag = element.tag_name
                    text = element.text.strip()
                    selenium_elements.append(f"Tag: {tag}, Text: {text}")

            return "\n".join(selenium_elements)
        except Exception as e:
            logger.error(f"Error extracting elements with Selenium: {e}")
            return "Error extracting elements with Selenium."

    def generate_openai_test_cases(self, description):
        """
        Generate test cases using OpenAI API based on extracted text or visual context.

        Args:
            description (str): Combined text and visual element description.

        Returns:
            list: A list of dictionaries containing structured test cases.
        """
        try:
            prompt = (
                f"Analyze the following GUI description and generate detailed test cases with the following structure:\n"
                f"1. Test Case ID\n"
                f"2. Test Case Description\n"
                f"3. Precondition\n"
                f"4. Test Steps\n"
                f"5. Expected Result\n\n"
                f"Description:\n{description}\n\n"
                f"Please provide 20 detailed test cases. Ensure they are well-structured for Excel export."
            )
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert software tester."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.5,
            )
            raw_test_cases = response["choices"][0]["message"]["content"].strip()

            # Parse the response into a structured format
            test_cases = []
            for idx, block in enumerate(raw_test_cases.split("\n\n"), start=1):
                test_case = {
                    "Test Case ID": f"TC{idx:03}",
                    "Test Case Description": None,
                    "Precondition": None,
                    "Test Steps": None,
                    "Expected Result": None,
                }

                lines = block.split("\n")
                for line in lines:
                    if "Test Case Description:" in line:
                        test_case["Test Case Description"] = line.split(":", 1)[1].strip()
                    elif "Precondition:" in line:
                        test_case["Precondition"] = line.split(":", 1)[1].strip()
                    elif "Test Steps:" in line:
                        test_case["Test Steps"] = line.split(":", 1)[1].strip()
                    elif "Expected Result:" in line:
                        test_case["Expected Result"] = line.split(":", 1)[1].strip()

                test_cases.append(test_case)

            return test_cases
        except Exception as e:
            logger.error(f"Failed to generate test cases: {e}")
            return [{"Test Case ID": "N/A", "Test Case Description": "Error generating test cases.", "Precondition": "N/A", "Test Steps": "N/A", "Expected Result": "N/A"}]

    def save_test_cases_to_excel(self, test_cases, file_path):
        """
        Save the test cases to an Excel file.

        Args:
            test_cases (list): List of dictionaries containing test case details.
            file_path (str): Path of the uploaded image file or generated for URL.
        """
        try:
            # Convert test cases to a DataFrame
            df = pd.DataFrame(test_cases)

            # Save the DataFrame to an Excel file
            output_file = os.path.splitext(file_path)[0] + "_test_cases.xlsx"
            df.to_excel(output_file, index=False, engine="openpyxl")
            logger.info(f"Test cases saved to {output_file}.")
        except Exception as e:
            logger.error(f"Failed to save test cases to Excel: {e}")

class MyApp(App):
    def build(self):
        return TestApp()

if __name__ == "__main__":
    MyApp().run()
