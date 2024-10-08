import requests
from datetime import datetime
import json
from openai import OpenAI
import os
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)
BASE_URL = os.environ.get("BASE_URL")

def check_item_exists(name):
    params = {
        "name": name.lower()
    }
    try:
        response = requests.get(f"{BASE_URL}/check-exists", params=params)
        print(f"Checking item: {name}")
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error checking item existence: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return False

def read_menu_data(filename):
    menu_data = {}
    current_date = None
    current_meal = None

    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith('Scraping'):
                parts = line.split()
                current_date = parts[-1]
                current_meal = parts[1]
                menu_data.setdefault(current_date, {}).setdefault(current_meal, [])
            elif line.startswith('Item:'):
                item_name = line.split(': ')[1]
                menu_data[current_date][current_meal].append(item_name)
    return menu_data

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, 'output.txt')
    menu_data = read_menu_data(filename)
    all_nutrition_data = []

    initial_messages = [
        {"role": "system", "content": "You estimate the calories of various items in a cafeteria, best as you can, and then give a response in JSON format, for the food items with their values, without showing any of the calculations. The content you display are the protein, fat, carbs, calories, isVegan, isVegetarian, isGlutenFree. Pay special attention making sure that the JSON is formatted correctly and is your only output. Also make sure to fully end the JSON every time. Also set the isVegan, isVegetarian, isGlutenFree to 'true' if true and 'false' if false. Make sure to give an estimate for every type of nutrient."},
        {"role": "user", "content": "Chicken Bacon Ranch Wrap"},
        {"role": "assistant", "content": "{ \"Item\": \"Chicken Bacon Ranch Wrap\", \"protein\": \"25g\", \"fat\": \"20g\", \"carbs\": \"45g\", \"calories\": \"480\", \"isVegan\": false, \"isVegetarian\": false, \"isGlutenFree\": false }"},
        {"role": "user", "content": "Cajun Tempeh"},
        {"role": "assistant", "content": "{ \"Item\": \"Cajun Tempeh\", \"protein\": \"15g\", \"fat\": \"10g\", \"carbs\": \"30g\", \"calories\": \"300\", \"isVegan\": true, \"isVegetarian\": true, \"isGlutenFree\": true }"}
    ]

    for date, meals in menu_data.items():
        for meal_type, items in meals.items():
            for item in items:
                print(f"Processing: {item} on {date} for {meal_type}")
                if not check_item_exists(item):
                    # If the item doesn't exist, query GPT for nutrition info
                    item_message = {"role": "user", "content": item}
                    print("Sending query for item:", item)

                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo-0125",
                        messages=initial_messages + [item_message],
                        temperature=0.4,
                        max_tokens=1024,
                        top_p=0.9,
                        frequency_penalty=0.1,
                        presence_penalty=0.1
                    )

                    last_response_content = response.choices[0].message.content
                    print("Received response for item:", item)
                    print(last_response_content)
                    nutrition_info = json.loads(last_response_content)
                else:
                    # If the item exists, use placeholder values
                    print(f"Item '{item}' already exists. Using placeholder values.")
                    nutrition_info = {
                        "Item": item,
                        "protein": "0g",
                        "fat": "0g",
                        "carbs": "0g",
                        "calories": "0",
                        "isVegan": False,
                        "isVegetarian": False,
                        "isGlutenFree": False
                    }

                all_nutrition_data.append({
                    "Date": date,
                    "MealType": meal_type,
                    "ItemName": item,
                    "Nutrition": nutrition_info
                })

    nutrition_info_path = os.path.join(script_dir, 'nutrition_info.json')
    with open(nutrition_info_path, 'w') as f:
        json.dump(all_nutrition_data, f, indent=4)

    print(f"Nutrition data saved to {nutrition_info_path}")

if __name__ == "__main__":
    main()