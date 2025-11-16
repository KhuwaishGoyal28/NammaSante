from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import timedelta
import requests
import json
import google.generativeai as genai
from googletrans import Translator

# ------------------ Initialize Flask ------------------
app = Flask(__name__)
app.secret_key = "your-secret-key"
app.permanent_session_lifetime = timedelta(days=7)

# ------------------ Initialize Firebase ------------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ------------------ API KEYS ------------------
WEATHER_API_KEY = "2f5c1e16cfa8b205481b6a69b28d2609"
GEMINI_API_KEY = "AIzaSyBdzxrdWf9jvEco9VhD1uaxNTlNLnffrKU"

# Initialize Translator
translator = Translator()

# Initialize Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# ------------------ State-City Mapping ------------------
STATE_CITY_MAPPING = {
    "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Purnia", "Darbhanga", "Arrah", "Begusarai", "Katihar", "Munger"],
    "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur", "Korba", "Durg", "Raigarh", "Rajnandgaon", "Jagdalpur", "Ambikapur", "Chirmiri"],
    "Goa": ["Panaji", "Margao", "Vasco da Gama", "Mapusa", "Ponda", "Bicholim", "Curchorem", "Sanquelim", "Canacona", "Pernem"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Junagadh", "Gandhinagar", "Anand", "Navsari"],
    "Haryana": ["Faridabad", "Gurugram", "Panipat", "Ambala", "Yamunanagar", "Rohtak", "Hisar", "Karnal", "Sonipat", "Panchkula"],
    "Himachal Pradesh": ["Shimla", "Manali", "Dharamshala", "Solan", "Mandi", "Kullu", "Chamba", "Hamirpur", "Una", "Bilaspur"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro Steel City", "Deoghar", "Hazaribagh", "Giridih", "Ramgarh", "Medininagar", "Chirkunda"],
    "Karnataka": ["Bangalore", "Mysore", "Hubli-Dharwad", "Mangalore", "Belgaum", "Davanagere", "Bellary", "Vijayapura", "Shivamogga"],
    "Meghalaya": ["Shillong", "Tura", "Jowai", "Nongstoin", "Williamnagar", "Baghmara", "Resubelpara", "Mairang", "Nongpoh", "Ampati"],
    "Mizoram": ["Aizawl", "Lunglei", "Champhai", "Saiha", "Kolasib", "Serchhip", "Lawngtlai", "Mamit", "Hnahthial", "Saitual"],
    "Nagaland": ["Dimapur", "Kohima", "Mokokchung", "Tuensang", "Wokha", "Zunheboto", "Mon", "Phek", "Kiphire", "Longleng"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Brahmapur", "Sambalpur", "Puri", "Balasore", "Bhadrak", "Baripada", "Jharsuguda"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Hoshiarpur", "Mohali", "Batala", "Pathankot", "Moga"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Bikaner", "Ajmer", "Alwar", "Bhilwara", "Sikar", "Pali"],
    "Sikkim": ["Gangtok", "Namchi", "Mangan", "Gyalshing", "Pelling", "Ravangla", "Soreng", "Rangpo", "Singtam", "Jorethang"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Erode", "Vellore", "Thoothukudi", "Dindigul"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Ramagundam", "Khammam", "Mahbubnagar", "Nalgonda", "Adilabad", "Suryapet"],
    "Tripura": ["Agartala", "Udaipur", "Dharmanagar", "Kailasahar", "Belonia", "Khowai", "Ambassa", "Teliamura", "Sabroom", "Sonamura"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Ghaziabad", "Agra", "Meerut", "Varanasi", "Prayagraj", "Bareilly", "Aligarh", "Moradabad"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Roorkee", "Haldwani", "Rishikesh", "Kashipur", "Rudrapur", "Pithoragarh", "Ramnagar", "Nainital"],
    "West Bengal": ["Kolkata", "Asansol", "Siliguri", "Durgapur", "Howrah", "Bardhaman", "Malda", "Baharampur", "Kharagpur", "Shantipur"],
    "Andaman and Nicobar Islands": ["Port Blair", "Diglipur", "Mayabunder", "Rangat", "Garacharma", "Bamboo Flat", "Neil Island", "Havelock Island", "Car Nicobar", "Campbell Bay"],
    "Chandigarh": ["Chandigarh"],
    "Dadra and Nagar Haveli and Daman and Diu": ["Daman", "Diu", "Silvassa", "Amli"],
    "Delhi": ["New Delhi", "Delhi"],
    "Jammu and Kashmir": ["Srinagar", "Jammu", "Anantnag", "Baramulla", "Udhampur", "Kathua", "Sopore", "Rajouri", "Poonch", "Kupwara"],
    "Ladakh": ["Leh", "Kargil"],
    "Lakshadweep": ["Kavaratti", "Agatti", "Amini", "Andrott", "Minicoy", "Kalpeni", "Kadmat", "Kiltan", "Chetlat", "Bitra"],
    "Puducherry": ["Puducherry", "Karaikal", "Mahe", "Yanam"]
}

# Make available in Jinja templates globally
@app.context_processor
def inject_state_city_mapping():
    return dict(state_city_mapping=STATE_CITY_MAPPING)


# ------------------ INDEX ------------------
@app.route("/")
def index():
    return redirect(url_for("login"))

# ------------------ SIGNUP ------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = {}
    if request.method == "POST":
        form = request.form
        email = form.get("email")
        password = form.get("password")
        confirm = form.get("confirm_password")

        if password != confirm:
            flash("Passwords do not match!", "danger")
            return render_template("signup.html", form=form)

        try:
            user = auth.create_user(email=email, password=password)
            uid = user.uid

            # Save user data in Firestore
            profile_data = {
                "UID": uid,
                "Email": email,
                "Farmer_Name": form.get("Farmer_Name"),
                "State": form.get("State"),
                "District": form.get("District"),
                "Crop_Name": form.get("Crop_Name"),
                "Season": form.get("Season"),
                "Area_Cultivated_Acres": form.get("Area_Cultivated_Acres"),
                "Expected_Yield_Tonnes": form.get("Expected_Yield_Tonnes"),
                "Actual_Yield_Tonnes": form.get("Actual_Yield_Tonnes"),
                "Market_Price_per_Tonne": form.get("Market_Price_per_Tonne"),
                "Soil_Type": form.get("Soil_Type")
            }

            try:
                db.collection("users").document(uid).set(profile_data)
                flash("Signup successful! Please log in.", "success")
                return redirect(url_for("login"))
            except Exception as e:
                # If set fails, delete the auth user
                auth.delete_user(uid)
                flash(f"Error saving profile: {str(e)}. Please check your Firestore quota.", "danger")
                return render_template("signup.html", form=form)

        except Exception as e:
            flash(f"Error creating account: {e}", "danger")
            return render_template("signup.html", form=form)

    return render_template("signup.html", form=form)

# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    form = {}
    if request.method == "POST":
        form = request.form
        email = form.get("email")
        password = form.get("password")
        try:
            user = auth.get_user_by_email(email)
            # NOTE: Firebase Admin SDK cannot verify passwords directly
            # You can implement Firebase Auth REST API for verifying passwords
            session.permanent = True
            session["uid"] = user.uid
            session["email"] = user.email
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        except Exception:
            flash("Invalid credentials or user not found!", "danger")
    return render_template("login.html", form=form)

# ------------------ FORGOT PASSWORD ------------------
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form.get("email")
        try:
            link = auth.generate_password_reset_link(email)
            flash(f"Password reset link sent to {email}.", "success")
        except Exception as e:
            flash(f"Error sending reset link: {e}", "danger")
    return render_template("forgot.html")

# ------------------ DASHBOARD ------------------
@app.route("/dashboard")
def dashboard():
    if "uid" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    uid = session["uid"]

    # Fetch user profile from Firestore
    try:
        profile_doc = db.collection("users").document(uid).get()
        profile = profile_doc.to_dict() if profile_doc.exists else {}
    except Exception as e:
        flash(f"Error loading profile: {str(e)}. Please check your Firestore quota.", "danger")
        profile = {}

    return render_template("dashboard.html", profile=profile)

@app.route("/food_chain")
def food_chain():
    if "uid" not in session:
        return redirect(url_for("login"))
    return render_template("food_chain.html")

# ------------------ CROP GUIDANCE CHATBOT ------------------
@app.route("/crop_guidance")
def crop_guidance():
    if "uid" not in session:
        return redirect(url_for("login"))
    return render_template("crop_guidance.html")

@app.route("/crop_guidance", methods=["POST"])
def crop_guidance_chat():
    if "uid" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    try:
        # Detect language of user input
        detected = translator.detect(user_message)
        detected_lang = detected.lang

        # Translate to English for Gemini
        if detected_lang != 'en':
            translated_message = translator.translate(user_message, src=detected_lang, dest='en').text
        else:
            translated_message = user_message

        # Create prompt for Gemini
        prompt = f"""
        You are an AI agricultural assistant. Provide helpful, accurate advice about farming, crops, and agriculture.
        User question (translated to English): {translated_message}
        Please provide a comprehensive but concise response in English.
        """

        # Get response from Gemini
        response = model.generate_content(prompt)
        english_response = response.text.strip()

        # Translate response back to user's language
        if detected_lang != 'en':
            final_response = translator.translate(english_response, src='en', dest=detected_lang).text
        else:
            final_response = english_response

        return jsonify({
            "response": final_response,
            "detected_lang": detected_lang
        })

    except Exception as e:
        print(f"Error in crop guidance: {str(e)}")
        return jsonify({"error": "Failed to get AI response. Please try again."}), 500

# ------------------ FARMER HELP DESK ------------------
@app.route("/farmer_help_desk", methods=["GET", "POST"])
def farmer_help_desk():
    if "uid" not in session:
        return redirect(url_for("login"))

    weather_info = None
    advice = None
    selected_state = None
    selected_city = None
    cities = []

    if request.method == "POST":
        selected_state = request.form.get("state")
        selected_city = request.form.get("city")

        # Get cities for selected state
        if selected_state in STATE_CITY_MAPPING:
            cities = STATE_CITY_MAPPING[selected_state]

        # Fetch weather data
        if selected_city:
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={selected_city}&appid={WEATHER_API_KEY}&units=metric"
            weather_resp = requests.get(weather_url)
            if weather_resp.status_code == 200:
                weather_data = weather_resp.json()
                weather_info = {
                    "temp": weather_data["main"]["temp"],
                    "humidity": weather_data["main"]["humidity"],
                    "description": weather_data["weather"][0]["description"]
                }

                # Send info to Gemini API for farming advice
                prompt = f"""
                I am a farmer in {selected_city}, {selected_state}.
                The current weather is {weather_info['description']}, temperature {weather_info['temp']}°C, humidity {weather_info['humidity']}%.
                Suggest best practices and tips to grow my crops effectively under these conditions.
                """
                response = model.generate_content(prompt)
                advice = response.text.strip()
            else:
                flash("Could not fetch weather data. Check city name.", "danger")
    else:
        # GET request: populate only states
        cities = []

    return render_template(
        "farmer_help_desk.html",
        weather=weather_info,
        advice=advice,
        selected_state=selected_state,
        selected_city=selected_city,
        states=list(STATE_CITY_MAPPING.keys()),
        cities=cities
    )

# ------------------ PROFILE ------------------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid = session["uid"]
    user_ref = db.collection("users").document(uid)
    if request.method == "POST":
        updated_data = {
            "Farmer_Name": request.form.get("Farmer_Name"),
            "State": request.form.get("State"),
            "District": request.form.get("District"),
            "Crop_Name": request.form.get("Crop_Name"),
            "Season": request.form.get("Season"),
            "Area_Cultivated_Acres": request.form.get("Area_Cultivated_Acres"),
            "Expected_Yield_Tonnes": request.form.get("Expected_Yield_Tonnes"),
            "Actual_Yield_Tonnes": request.form.get("Actual_Yield_Tonnes"),
            "Market_Price_per_Tonne": request.form.get("Market_Price_per_Tonne"),
            "Soil_Type": request.form.get("Soil_Type"),
            "Water_Usage_Liters_per_Acre": request.form.get("Water_Usage_Liters_per_Acre"),
            "Fertilizer_Usage_kg_per_Acre": request.form.get("Fertilizer_Usage_kg_per_Acre"),
            "Sustainability_Score": request.form.get("Sustainability_Score"),
            "Weather_Condition": request.form.get("Weather_Condition"),
            "Predicted_Demand_for_Next_Season_Tonnes": request.form.get("Predicted_Demand_for_Next_Season_Tonnes"),
            "Overproduction_Risk": request.form.get("Overproduction_Risk"),
            "Date_Recorded": request.form.get("Date_Recorded")
        }
        try:
            user_ref.update(updated_data)
            flash("Profile updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating profile: {str(e)}. Please check your Firestore quota.", "danger")
        return redirect(url_for("profile"))

    try:
        profile_doc = user_ref.get()
        profile = profile_doc.to_dict() if profile_doc.exists else {}
    except Exception as e:
        flash(f"Error loading profile: {str(e)}. Please check your Firestore quota.", "danger")
        profile = {}
    return render_template("profile.html", profile=profile)

# ------------------ Availability Route ------------------
@app.route("/availability", methods=["GET", "POST"])
def availability():
    if request.method == "POST":
        selected_state = request.form.get("state")
        selected_city = request.form.get("city")

        farmers = []
        try:
            # Fetch farmers from Firestore matching the state and city
            farmers_ref = db.collection("users")
            query = farmers_ref.where("State", "==", selected_state).where("District", "==", selected_city)
            farmers = [doc.to_dict() for doc in query.stream()]
            print(f"Selected state: {selected_state}, city: {selected_city}")
            print(f"Farmers fetched: {len(farmers)}")
        except Exception as e:
            flash(f"Error fetching availability data: {str(e)}. Please check your Firestore quota.", "danger")

        return render_template(
            "availability.html",
            state_city_mapping=STATE_CITY_MAPPING,
            selected_state=selected_state,
            selected_city=selected_city,
            farmers=farmers,
        )

    return render_template("availability.html", state_city_mapping=STATE_CITY_MAPPING)

# ------------------ Demand Route ------------------
@app.route("/demand", methods=["GET", "POST"])
def demand():
    demand_data = []
    if request.method == "POST":
        selected_state = request.form.get("state")
        selected_city = request.form.get("city")

        farmers = []
        try:
            # Fetch farmers from Firestore matching the state and city
            farmers_ref = db.collection("users")
            query = farmers_ref.where("State", "==", selected_state).where("District", "==", selected_city)
            farmers = [doc.to_dict() for doc in query.stream()]
            print(f"Selected state: {selected_state}, city: {selected_city}")
            print(f"Farmers fetched: {len(farmers)}")
        except Exception as e:
            flash(f"Error fetching demand data: {str(e)}. Please check your Firestore quota.", "danger")

        # Aggregate demand by crop
        crop_demand = {}
        for farmer in farmers:
            crop = farmer.get("Crop_Name", "Unknown")
            yield_tonnes = float(farmer.get("Expected_Yield_Tonnes", 0))
            if crop in crop_demand:
                crop_demand[crop] += yield_tonnes
            else:
                crop_demand[crop] = yield_tonnes

        demand_data = [{"crop": crop, "total_needed": total} for crop, total in crop_demand.items()]

        return render_template(
            "demand.html",
            state_city_mapping=STATE_CITY_MAPPING,
            selected_state=selected_state,
            selected_city=selected_city,
            demand_data=demand_data,
        )

    return render_template("demand.html", state_city_mapping=STATE_CITY_MAPPING)


# ------------------ DELETE ACCOUNT ------------------
@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid = session["uid"]
    try:
        # Delete user from Firebase Authentication
        auth.delete_user(uid)

        # Delete user data from Firestore
        db.collection("users").document(uid).delete()

        # Clear session
        session.clear()
        flash("Your account has been deleted successfully.", "success")
        return redirect(url_for("signup"))
    except Exception as e:
        flash(f"Error deleting account: {str(e)}. Please check your Firestore quota.", "danger")
        return redirect(url_for("profile"))

# ------------------ LOGOUT ------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
