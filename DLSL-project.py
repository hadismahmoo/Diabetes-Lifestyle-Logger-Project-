import json
import os
from datetime import date, datetime, timedelta
from openai import OpenAI

#::Patient Classification::
class Patient_info:
    def __init__(self, name, age, diabetes_type, weight, height, physical_activity, uses_glucometer, patient_ID, medications):
        self.name = name
        self.age = age
        self.diabetes_type = diabetes_type
        self.weight = weight
        self.height = height
        self.physical_activity = physical_activity
        self.uses_glucometer = uses_glucometer.lower()
        self.patient_ID = patient_ID
        self.medications = medications

        self.patient_info = {
            'patient_ID': self.patient_ID,
            'name': self.name,
            'age': int(self.age),
            'Diabetes_type': self.diabetes_type,
            'Medications': self.medications,
            'Weight': float(self.weight),
            'Height': float(self.height),
            'BMI': round(float(self.weight) / float(self.height) ** 2, 2),
            'Physical_activity': self.physical_activity,
            'Uses_Glucometer': self.uses_glucometer
        }

        self.other_diabetes = [
            'Gestational', 'MODY', 'Neonatal', 'Wolfram', 'LADA',
            '3c', 'Steroid-induced', 'Cyctic_fibrosis'
        ]

    def dictionary(self):
        while True:
            try:
                if int(self.age) <= 0 or int(self.age) > 100:
                    print('Please enter a valid number for your age.')
                    self.age = input('Enter your age again: ')
                    continue
            except ValueError:
                print('Age should be a number.')
                self.age = input('Enter your age again: ')
                continue

            if self.diabetes_type in self.other_diabetes:
                print('This program is not made for your type of diabetes.')
                return None
            elif self.diabetes_type not in ['1', '2']:
                print('Please enter your diabetes type again (1 or 2).')
                self.diabetes_type = input('Enter your type again: ')
                continue

            if len(self.patient_ID) < 8:
                print('Your ID should have at least 8 characters.')
                self.patient_ID = input('Enter your ID again: ')
                continue
            elif self.patient_ID.isalpha():
                print('Your ID should have at least one number.')
                self.patient_ID = input('Enter your ID again: ')
                continue
            elif self.patient_ID.isnumeric():
                print('Your ID should have at least one word.')
                self.patient_ID = input('Enter your ID again: ')
                continue

            return self.patient_info


#::Glycemic Load Calculation::
def calculate_gl_for_meal(meal, foods_data):
    total_gl = 0
    for item in meal:
        food = item['food']
        grams = item['grams']
        if food in foods_data:
            gi = foods_data[food]['GI']
            cf = foods_data[food]['CF']
            gl = (gi / 100) * (grams * cf)
            total_gl += gl
        else:
            print(f"Warning: {food} not found in FOODS.json. Skipping.")
    return round(total_gl, 2)


def daily_taken_food(patient_ID, today_date, uses_glucometer):
    try:
        with open('FOODS.json', 'r', encoding='utf-8') as f:
            foods_data = json.load(f)
    except FileNotFoundError:
        foods_data = {}

    daily_entry = {}
    if uses_glucometer == "yes":
        for meal_name in ["Breakfast", "Lunch", "Dinner", "Snack"]:
            bg_level = input(f"Enter your blood glucose level after {meal_name} (mg/dL): ").strip()
            daily_entry[meal_name] = {"Blood_Glucose": bg_level}
        daily_entry["GL_error"] = "Recorded from glucometer readings."
    else:
        total_gl = 0
        for meal_name in ["Breakfast", "Lunch", "Dinner", "Snack"]:
            print(f"\nEnter foods for {meal_name} (press Enter without food name to finish):")
            meal_list = []
            while True:
                food = input("Food name: ").strip()
                if food == "":
                    break
                grams = float(input(f"Grams of {food}: "))
                meal_list.append({"food": food, "grams": grams})
            daily_entry[meal_name] = meal_list
            total_gl += calculate_gl_for_meal(meal_list, foods_data)

        daily_entry["Total_GL"] = round(total_gl, 2)
        daily_entry["GL_error"] = "Please eat healthier tomorrow" if total_gl > 100 else "You ate healthy today."

    try:
        with open('daily_data.json', 'r', encoding='utf-8') as f:
            daily_data = json.load(f)
    except FileNotFoundError:
        daily_data = {}

    if patient_ID not in daily_data:
        daily_data[patient_ID] = {}

    daily_data[patient_ID][today_date] = daily_entry

    with open('daily_data.json', 'w', encoding='utf-8') as f:
        json.dump(daily_data, f, indent=4, ensure_ascii=False)

    print("Daily record saved successfully!")


#::Check Medication::
def check_medications(patient_ID):
    current_time = datetime.now()
    try:
        with open("DLSLinfo.json", "r", encoding="utf-8") as file:
            patients = json.load(file)
    except FileNotFoundError:
        print("DLSLinfo.json not found.")
        return

    for patient in patients:
        if patient["patient_ID"] == patient_ID:
            medications = patient.get("Medications", [])
            for medicine in medications:
                name = medicine.get("name")
                time_str = medicine.get("time", "").strip()
                frequency = str(medicine.get("frequency", "")).lower().strip()

                try:
                    base_time = datetime.strptime(time_str, "%H:%M")
                    base_time = current_time.replace(hour=base_time.hour, minute=base_time.minute, second=0, microsecond=0)

                    if "2" in frequency: times_per_day = 2
                    elif "3" in frequency: times_per_day = 3
                    elif "4" in frequency: times_per_day = 4
                    else: times_per_day = 1

                    interval = 24 // times_per_day
                    for i in range(times_per_day):
                        dose_time = base_time + timedelta(hours=i * interval)
                        if abs(current_time - dose_time) <= timedelta(minutes=5):
                            print(f"Time to take {name} — scheduled at {dose_time.strftime('%H:%M')}")
                            break
                except ValueError:
                    print(f"Invalid time format for {name}: {time_str}")
            return
    print("This ID does not exist.")


#::Patient's Exercise Plan::
def exercise_schedule(patient_ID):
    try:
        with open("DLSLinfo.json", "r", encoding="utf-8") as file:
            patients = json.load(file)
    except FileNotFoundError:
        print("DLSLinfo.json not found.")
        return

    try:
        with open("DLSLAPI.txt", "r", encoding="utf-8") as file:
            API_key = file.read().strip()
    except FileNotFoundError:
        print("DLSLAPI.txt not found. Cannot generate exercise plan.")
        return

    Base_URL = "https://api.avalai.ir/v1"

    patient = next((p for p in patients if p.get("patient_ID") == patient_ID), None)
    if not patient:
        print(f"Patient ID {patient_ID} does not exist.")
        return

    Age = patient.get("age")
    diabetes_type = patient.get("Diabetes_type")
    bmi = patient.get("BMI")
    physical_activity = patient.get("Physical_activity", "").lower()

    if physical_activity != "no":
        print("Patient already has physical activity. No schedule needed.")
        return

    client = OpenAI(api_key=API_key, base_url=Base_URL)
    prompts = [
        {"role": "system", "content": "You are a health and fitness assistant who creates safe, personalized weekly exercise plans."},
        {"role": "user", "content": f"Give a weekly exercise schedule to a {Age}-year-old patient with BMI {bmi} and type {diabetes_type} diabetes who currently has no physical activity."}
    ]
    response = client.chat.completions.create(model="gpt-4.1-nano", messages=prompts, temperature=0.7)
    answer = response.choices[0].message.content

    file_name = f"weekly_exercise_plan_{patient_ID}.txt"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(answer)

    print(f"Exercise plan saved in '{file_name}'")


#::Final runner code ::
if __name__ == "__main__":
    # Ask for patient ID first
    patient_ID = input("Enter your patient ID: ").strip()

    try:
        with open("DLSLinfo.json", "r", encoding="utf-8") as file:
            patients = json.load(file)
    except FileNotFoundError:
        patients = []

    patient = next((p for p in patients if p["patient_ID"] == patient_ID), None)

    if patient:
        print(f"Welcome back, {patient['name']}!")
        uses_glucometer = patient.get("Uses_Glucometer", "no")
    else:
        print("No existing record found. Let's create your profile.")
        name = input('What is your name? ')
        age = input('How old are you? ')
        diabetes_type = input('What type of diabetes do you have (1 or 2)? ')
        weight = input('Enter your weight in kg: ')
        height = input('Enter your height in meters: ')
        physical_activity = input('Do you have any physical activity (yes or no)? ')
        uses_glucometer = input('Do you use a glucometer? (yes/no): ').strip().lower()

        medications = []
        while True:
            med_name = input("Enter the name of a medicine you take (or press Enter to finish): ").strip()
            if med_name == "":
                break
            med_time = input(f"Enter the time you take {med_name} (HH:MM): ").strip()
            med_frequency = input(f"Enter how often you take {med_name} (e.g., 2 times a day): ").strip()
            medications.append({"name": med_name, "time": med_time, "frequency": med_frequency})

        new_patient = Patient_info(name, age, diabetes_type, weight, height, physical_activity, uses_glucometer, patient_ID, medications)
        info = new_patient.dictionary()
        if info:
            patients.append(info)
            with open("DLSLinfo.json", "w", encoding="utf-8") as file:
                json.dump(patients, file, indent=4, ensure_ascii=False)
            print("Patient data saved!")

    
    check_medications(patient_ID)
    today_date = str(date.today())
    daily_taken_food(patient_ID, today_date, uses_glucometer)
    exercise_schedule(patient_ID)
