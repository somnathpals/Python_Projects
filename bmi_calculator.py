height = float(input("Enter your height in meters upto 2nd decimal: "))
weight = float(input("Enter your weight in kg: "))

# Write your code here.
# Calculate the bmi using weight and height.
bmi = (weight / height**2)
print(("Your BMI is:") + " " + str(round(bmi,2)))
print(" ")
if bmi < 18.5:
    print("You are underweight")
elif bmi >= 18.5 and bmi < 25:
    print("You are normal weight")
else:
    print("You are overweight")
