import streamlit as st

st.set_page_config(page_title= 'BMI Calculator App', layout= 'centered')
st.title("BMI Calculator")

# Use st.number_input for numerical inputs instead of input()
height = st.number_input(
    "Enter your height in meters (e.g., 1.75):",
    #min_value=0.1,
    #max_value=3.0,
    #step=0.01,
    #format="%.2f"
)
weight = st.number_input(
    "Enter your weight in kg (e.g., 70):",
    #min_value=1.0,
    #max_value=500.0,
    #step=0.1
)

# Use a button to trigger the calculation only when ready
if st.button("Calculate BMI"):
    if height > 0 and weight > 0:
        # Calculate the bmi using weight and height.
        bmi = (weight / height**2)
        
        # Use st.success, st.warning, st.info for formatted output instead of print()
        st.subheader(f"Your BMI is: **{round(bmi, 2)}**")

        if bmi < 18.5:
            st.info("You are underweight")
        elif bmi >= 18.5 and bmi < 25:
            st.success("You are normal weight")
        else:
            st.warning("You are overweight")
    else:
        st.error("Please enter valid height and weight values.")