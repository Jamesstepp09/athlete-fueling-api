from flask import Flask, request, jsonify
import tempfile
import os
import traceback
import json as json_lib
import anthropic
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName, FileType, Disposition
)
from pdf_generator import generate_plan

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
SENDGRID_API_KEY  = os.environ.get("SENDGRID_API_KEY")
DELIVERY_EMAIL    = os.environ.get("DELIVERY_EMAIL")

SYSTEM_PROMPT = """You are an expert sports dietitian and performance nutritionist with advanced credentials in sports science. You generate fully personalized, evidence-based athlete fueling plans using published guidelines from ISSN, ACSM, AAP, and the Dietary Guidelines for Americans 2020-2025.

Your output is ALWAYS a single valid JSON object. No markdown. No code fences. No preamble. No explanation. Just the raw JSON object starting with { and ending with }. Any deviation from this will break the downstream PDF pipeline.

---

CALCULATION METHODOLOGY - follow these exactly:

BMR CALCULATION (Harris-Benedict Revised):
  Male:   BMR = 88.362 + (13.397 x kg) + (4.799 x cm) - (5.677 x age)
  Female: BMR = 447.593 + (9.247 x kg) + (3.098 x cm) - (4.330 x age)
  Convert lbs to kg: divide by 2.205
  Convert height to cm: feet x 30.48 + inches x 2.54

TDEE (Total Daily Energy Expenditure):
  Multiply BMR by sport-specific activity multiplier:
  - Sedentary / rest day:        x 1.2
  - Light activity (1 hr/day):   x 1.375
  - Moderate (1-2 hrs/day):      x 1.55
  - High (2-3 hrs/day):          x 1.725
  - Very high (3+ hrs/day):      x 1.9

CALORIE TARGETS:
  Training day: TDEE at high/very high multiplier
  Rest day:     TDEE at sedentary multiplier
  Lift day:     Training day + 300-400 kcal

PROTEIN TARGETS BY SPORT TYPE:
  Team sport / field sport:      1.6-2.0 g/kg
  Endurance (running, cycling):  1.4-1.7 g/kg
  Powerlifting / strength:       1.8-2.5 g/kg
  Bodybuilding / physique:       2.0-3.0 g/kg (bulking), 2.3-3.1 g/kg (cutting)
  Combat sports / wrestling:     1.8-2.3 g/kg
  Swimming / gymnastics:         1.6-2.0 g/kg

CARBOHYDRATE TARGETS BY SPORT TYPE:
  Team / field sport:            6-8 g/kg training, 4-5 g/kg rest
  Endurance (high volume):       8-12 g/kg training, 5-6 g/kg rest
  Powerlifting / strength:       4-6 g/kg training, 3-4 g/kg rest
  Bodybuilding (bulk):           4-7 g/kg; (cut): 2-4 g/kg
  Combat sports:                 5-7 g/kg training, 3-4 g/kg rest

FAT TARGETS: Fill remaining calories after protein and carbs are set.
  General range: 0.8-1.5 g/kg. Never below 20% of total calories.

---

MEAL TIMING RULES - personalize around the athlete's exact schedule:
  Pre-training meal: 2-3 hours before practice start time. Large, carb-dominant.
  Pre-training snack: 60-90 min before practice. Moderate carbs, low fat.
  During training: Hydration every 15-20 min. Carbs if session >75 min.
  Post-training window: Within 30 minutes of session end. Protein + carbs, fast-absorbing.
  Sleep nutrition: 30-60 min before bed. Casein or slow-digesting protein.
  Use exact clock times (e.g. "2:30 PM") not relative timing.

---

SPORT-SPECIFIC PROTOCOL RULES:

TEAM / FIELD SPORTS (soccer, basketball, lacrosse, field hockey, rugby):
  - Game-day protocol: pre-game 3-4 hrs, top-off 60-90 min, halftime, post-game
  - Creatine: strong evidence for repeat sprint performance
  - Electrolytes: critical in outdoor heat

ENDURANCE (running, cycling, triathlon, swimming, rowing, cross-country):
  - Very high carb periodization (8-12 g/kg)
  - Fueling DURING exercise is critical (30-60g carbs/hr for efforts >90 min)
  - No game-day protocol - use race-day / long run protocol instead
  - Carbohydrate loading section replaces game-day if applicable
  - Beta-alanine and sodium bicarbonate: evidence-based for endurance
  - Iron: high depletion risk, especially female distance runners

POWERLIFTING / STRENGTH SPORTS:
  - Very high protein (1.8-2.5 g/kg)
  - Creatine: strongest evidence of any sport category
  - Meet-day protocol replaces game-day protocol
  - Weight class management section if athlete is cutting

BODYBUILDING / PHYSIQUE:
  - Bulking phase: caloric surplus 250-500 kcal above TDEE
  - Cutting phase: caloric deficit 300-500 kcal below TDEE, high protein to preserve muscle
  - No game-day protocol - use competition prep section if in prep
  - Peak week: water/sodium/carbohydrate manipulation guidance

COMBAT SPORTS (wrestling, MMA, boxing, judo):
  - Weight cut section if athlete cuts weight for competition
  - Rehydration protocol post-weigh-in
  - Competition-day fueling between weigh-in and bout
  - High protein, moderate carbs

---

SUPPLEMENT SELECTION RULES:
  Only recommend supplements that fill a GENUINE gap not met by diet at the athlete's training volume.
  Evidence tiers:
    STRONG EVIDENCE: Multiple RCTs, ISSN Position Stand, broad scientific consensus
    GOOD EVIDENCE:   Solid mechanistic data, some RCTs, minor conflicting studies
    SITUATIONAL:     Useful in specific contexts (heat, travel, weight class sports)
  Do NOT recommend a supplement the athlete is already taking.
  Adolescent athletes (<18): exclude high-dose caffeine, testosterone boosters, fat burners.
  Always include NSF Certified for Sport or Informed Sport recommendation.

---

INJURY PREVENTION - include this section if:
  - Athlete is in pre-season or competition prep
  - Athlete reported an injury or recovery status
  - Sport has high soft tissue injury rate
  - Athlete is adolescent

---

DIET GAP ANALYSIS - based on "typical day of eating":
  Identify 2-4 genuine strengths
  Identify 3-6 gaps the plan directly addresses
  Be specific - "skips breakfast" not "suboptimal morning nutrition"

---

OUTPUT FORMAT - strict JSON schema. Every key is required.
  Use plain ASCII hyphens (-) not en-dashes in all strings.
  Do not use Unicode special characters in any string values.
  Meal "items" arrays: each item is one bullet point of food. 3-6 items per meal.
  "macros" string format: "~XXX kcal  /  Xg protein  /  Xg carbs"
  Evidence badge must be exactly one of: "STRONG EVIDENCE" "GOOD EVIDENCE" "SITUATIONAL"
  week_days: exactly 7 strings
  week_overview_rows: maximum 7 rows. Each row is [row_label, day1, day2, day3, day4, day5, day6, day7]
  show_injury_section: boolean true or false

{
  "name": "string",
  "plan_title": "string",
  "sport": "string",
  "position": "string",
  "club": "string",
  "age": "string",
  "height": "string",
  "weight_lbs": "string",
  "training_kcal": "string",
  "rest_kcal": "string",
  "protein_range": "string",
  "season_phase": "string",
  "schedule_summary": "string",
  "primary_goal": "string",
  "restrictions": "string",
  "science_blurb": "string",
  "macro_table": [
    ["Carbohydrates", "Xg/kg | Xg", "Xg/kg | Xg", "Xg/kg | Xg", "food sources"],
    ["Protein",       "Xg/kg | Xg", "Xg/kg | Xg", "Xg/kg | Xg", "food sources"],
    ["Fat",           "Xg/kg | Xg", "Xg/kg | Xg", "Xg/kg | Xg", "food sources"],
    ["Hydration",     "X.X L total", "X.X L total", "X.X L total", "water + electrolytes"]
  ],
  "training_day_meals": [
    {"time": "HH:MM AM/PM  --  Meal Name", "title": "Meal Name", "macros": "~XXX kcal  /  Xg protein  /  Xg carbs", "items": ["food item 1", "food item 2", "food item 3"]}
  ],
  "rest_day_intro": "string",
  "rest_day_meals": [
    {"time": "HH:MM AM/PM  --  Meal Name", "title": "Meal Name", "macros": "~XXX kcal  /  Xg protein  /  Xg carbs", "items": ["food item 1", "food item 2", "food item 3"]}
  ],
  "lift_day_intro": "string",
  "lift_dos": ["do item 1", "do item 2", "do item 3", "do item 4", "do item 5"],
  "lift_donts": ["avoid item 1", "avoid item 2", "avoid item 3", "avoid item 4", "avoid item 5"],
  "game_day_rows": [["timing string", "what to eat string", "why it matters string"]],
  "hydration_blurb": "string",
  "hydration_rows": [["time of day", "target oz or L", "notes"]],
  "supplement_intro": "string",
  "supplements": [
    {"name": "Supplement Name", "evidence": "STRONG EVIDENCE", "dose": "dose string", "timing": "timing string", "description": "2-3 sentence rationale with mechanism and source citation"}
  ],
  "supplements_avoid": "string",
  "goal_blurb": "string",
  "goal_points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "sleep_blurb": "string",
  "sleep_rows": [["nutrient or strategy", "dose / timing", "purpose"]],
  "show_injury_section": true,
  "injury_blurb": "string",
  "injury_rows": [["nutrient", "dose / source", "timing", "why it matters"]],
  "diet_strengths": ["strength 1", "strength 2", "strength 3"],
  "diet_gaps": ["gap 1", "gap 2", "gap 3", "gap 4", "gap 5"],
  "week_days": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
  "week_overview_rows": [
    ["Training", "day1", "day2", "day3", "day4", "day5", "day6", "day7"],
    ["Calories", "~XXXX", "~XXXX", "~XXXX", "~XXXX", "~XXXX", "~XXXX", "~XXXX"],
    ["Protein",  "XXXg", "XXXg", "XXXg", "XXXg", "XXXg", "XXXg", "XXXg"],
    ["Carbs",    "XXXg", "XXXg", "XXXg", "XXXg", "XXXg", "XXXg", "XXXg"],
    ["Creatine", "post", "--", "post", "--", "post", "--", "--"],
    ["Tart Cherry", "nightly", "nightly", "nightly", "nightly", "nightly", "nightly", "nightly"],
    ["Collagen", "pre-train", "pre-train", "pre-train", "pre-train", "pre-train", "pre-game", "--"]
  ],
  "disclaimer": "IMPORTANT NOTICE - This performance fueling plan is an AI-assisted document based on published guidelines from ISSN, ACSM, AAP, and the Dietary Guidelines for Americans 2020-2025. It is designed as a general evidence-based framework for performance nutrition education and is not a substitute for individualized medical or dietetic advice. Specific caloric needs, supplement tolerances, and health status should be reviewed by a licensed Registered Dietitian (RD) with Certified Specialist in Sports Dietetics (CSSD) credential and a primary care physician before implementing any supplement protocol. If the athlete experiences fatigue, GI distress, mood changes, or performance decline, consult a healthcare provider promptly.",
  "sources_line": "string (list 6-10 primary source citations relevant to this sport and supplement stack)"
}"""


def extract_fields(tally_payload):
    """Extract field values from Tally webhook payload into a flat dict."""
    fields = {}
    try:
        data = tally_payload.get("data", {})
        for field in data.get("fields", []):
            label = field.get("label", "")
            value = field.get("value", "")
            options = field.get("options", [])
            option_map = {o.get("id"): o.get("text") for o in options}

            if isinstance(value, list):
                resolved = [option_map.get(v, str(v)) for v in value if v]
                value = ", ".join(r for r in resolved if r)
            elif isinstance(value, str) and value in option_map:
                value = option_map[value]

            fields[label] = value or ""

        # Debug: print all field labels received
        print("=== TALLY FIELDS RECEIVED ===")
        for k, v in fields.items():
            print(f"  [{k}] = {str(v)[:80]}")
        print("=== END FIELDS ===")

    except Exception as e:
        print(f"Error extracting fields: {e}")
        traceback.print_exc()
    return fields


def build_user_message(fields):
    """Build Claude user message from extracted Tally fields."""
    def get(key, default="Not provided"):
        v = fields.get(key, "")
        return v if v else default

    return f"""Generate a complete personalized performance fueling plan for the following athlete. Output only the JSON object. No markdown, no explanation, no code fences. Start with {{ and end with }}.

Fields marked as blank or Not provided should be ignored - some questions are optional and some are conditional on previous answers. Build the plan using only the populated fields.

---

PAGE 1 - PERSONAL INFORMATION

First name: {get('First Name')}
Last name: {get('Last Name')}
Email address: {get('Email Address')}
Phone number: {get('Phone Number (optional)')}

---

PAGE 2 - ATHLETE PROFILE

Biological sex: {get('Biological Sex')}
Date of birth: {get('Date of Birth')}
Height: {get('Height')}
Weight (lbs): {get('Weight (lbs)')}
Sport: {get('Sport')}
Position or role: {get('Position or role')}
Daily schedule: {get('Briefly describe your daily schedule')}

---

PAGE 3 - TRAINING & SEASON

What best describes your sport: {get('What best describes your sport?')}

[TEAM SPORT / INDIVIDUAL SPORT - shown if Team sport or Individual sport with competition season]
Current season phase: {get('Current Season Phase')}
Training days per week: {get('Training Days Per Week')}
Typical session length: {get('Typical Session Length')}
Do you do strength or weight training: {get('Do you do strength or weight training?')}
How many days per week do you lift: {get('How many days per week do you lift?')}
Do you have game days: {get('Do you have Game Days')}
What day(s) of the week: {get('What day(s) of the week')}
Training environment: {get('Training Environment')}

[STRENGTH / PHYSIQUE SPORT - shown if Strength or physique sport]
Do you have a competition scheduled: {get('Strength or physique - Do you have a competition scheduled?')}
What is the competition: {get('Strength or physique --What is the competition')}
How many weeks out: {get('Strength or physique - How many weeks out are you')}
Current prep phase: {get('Strength or physique - Current prep phase')}
Current focus (if not competing): {get('Strength or physique - Current Focus')}
How long have you been training: {get('Strength or physique - How long have you been training')}
Training days per week: {get('Strength or physique - Training days per week')}
Typical session length: {get('Strength or physique - Typical session length')}
Training split: {get('Strength or physique - What does your training split look like?')}

[COMBAT SPORT - shown if Combat sport]
Current season phase: {get('Combat - Current season phase')}
Do you need to cut weight for a weigh-in: {get('Combat - Do you need to cut weight for a weigh-in?')}
How much and by when: {get('Combat - How much and by when?')}
Training days per week: {get('Combat - Training days per week')}
Typical session length: {get('Combat - Typical session length')}

[ENDURANCE SPORT - shown if Endurance sport]
Primary endurance discipline: {get('What is your primary endurance discipline?')}
Season phase: {get('Endurance - Season phase')}
Training days per week: {get('Endurance - Training days/week')}
Typical weekly training volume: {get('Endurance - Typical weekly training volume')}
Typical session length: {get('Endurance - Typical session length')}
Do you also do strength training: {get('Endurance - Do you also do strength training?')}
How many days per week (strength): {get('Endurance - How many days per week?')}
Training environment: {get('Endurance - Training environment')}
Do you have a major event or race coming up: {get('Endurance - Do you have a major event or race coming up?')}
What is the event: {get('Endurance - What is the event?')}
Approximate event duration: {get('Endurance - Approximate event duration')}
How many weeks out: {get('Endurance - How many weeks out are you?')}
Have you done this event or distance before: {get('Endurance - Have you done this event or distance before?')}
Have you had GI issues during past races or long training sessions: {get('Endurance - Have you had any GI issues during past races or long training sessions?')}
What do you currently use for in-session fueling on long efforts: {get('Endurance - What do you currently use for in-session fueling on long efforts?')}

[ALL SPORT TYPES - always shown]
Are you recovering from an injury: {get('Are you recovering from an injury?')}
Injury details and recovery phase: {get('What is the injury and what phase of recovery are you in?')}
Do you track your nutrition currently: {get('Do you track your nutrition currently?')}

---

PAGE 4 - GOALS

Primary goal: {get('Primary goal')}
What does success look like for you: {get('What does success look like for you?')}
How important is diet flexibility to you: {get('How important is diet flexibility to you?')}

---

PAGE 5 - NUTRITION & RESTRICTIONS

Describe a typical day of eating: {get('Describe a typical day of eating')}
Do you eat breakfast before school or training: {get('Do you eat breakfast before school or training?')}
Do you eat anything before practice or training: {get('Do you eat anything before practice or training?')}
Any food allergies or intolerances: {get('Any food allergies or intolerances?')}
Any dietary preferences or restrictions: {get('Any dietary preferences or restrictions?')}
Foods you strongly dislike or refuse to eat: {get('Foods you strongly dislike or refuse to eat')}
Supplements currently taking: {get('Are you currently taking any supplements?')}
Other supplements (specify): {get('If you selected other, please specify')}
Peptide/PED approach: {get('What best describes your current peptide/PED approach?')}
Compounds currently using: {get('Which compounds are you currently using?')}

---

PAGE 6 - HEALTH & BACKGROUND

Average sleep per night: {get('How many hours of sleep do you get on a typical night?')}
Current injuries or physical limitations: {get('Any current injuries or physical limitations we should know about?')}
Diagnosed medical conditions or medications: {get('Any diagnosed medical conditions or medications relevant to your nutrition?')}
Please describe condition or medication: {get('Please describe your condition or medication')}

---

PROTOCOL SELECTION - apply silently based on sport type field:

Team sport / Individual sport with competition season:
Use the daily schedule to place meals at specific clock times. Apply game-day protocol. Season phase drives carbohydrate periodization. Account for lift frequency. Electrolytes critical if training environment is outdoors in heat.

Strength or physique sport:
Use daily schedule for gym timing only. Set calorie surplus (bulking/off-season) or deficit (cutting/contest prep) based on current focus or prep phase. If peak week, include water/sodium/carbohydrate manipulation. Very high protein. Replace game-day with meet-day or competition-day protocol.

Combat sport:
If weight cut indicated, include pre-weigh-in cut protocol and post-weigh-in rehydration. Replace game-day with bout-day protocol. High protein, moderate carb.

Endurance sport:
Apply high carbohydrate periodization - 8-12 g/kg on long training days. Include intra-workout fueling (30-60g carbs/hr for sessions over 90 min). If GI issues reported, use low-FODMAP fueling strategy. Replace game-day with race-day protocol scaled to event duration. If within 2 weeks of event, include carbohydrate loading protocol."""


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Parse Tally payload
        raw = request.get_data(as_text=False).decode("utf-8")
        tally_payload = json_lib.loads(raw)
        print("=== TALLY WEBHOOK RECEIVED ===")

        # Extract fields
        fields = extract_fields(tally_payload)

        first_name = fields.get("First Name", "").strip()
        last_name  = fields.get("Last Name", "").strip()
        athlete_name = f"{first_name} {last_name}".strip() or "Unknown Athlete"
        athlete_email = fields.get("Email Address", "").strip()
        sport = fields.get("Sport", "Unknown Sport")

        print(f"=== ATHLETE: {athlete_name} | {athlete_email} | {sport} ===")

        # Call Claude API
        print("=== CALLING CLAUDE API ===")
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            temperature=0.2,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(fields)}]
        )
        plan_json_str = message.content[0].text
        print(f"=== CLAUDE RESPONSE LENGTH: {len(plan_json_str)} chars ===")

        # Parse JSON
        athlete_data = json_lib.loads(plan_json_str)
        print("=== JSON PARSED SUCCESSFULLY ===")

        # Generate PDF
        print("=== GENERATING PDF ===")
        safe_name = athlete_name.replace(" ", "_").replace("/", "_")
        tmp = tempfile.NamedTemporaryFile(
            suffix=".pdf",
            prefix=f"{safe_name}_",
            delete=False
        )
        tmp.close()
        generate_plan(athlete_data, output_path=tmp.name)
        print(f"=== PDF GENERATED ===")

        # Read and encode PDF
        with open(tmp.name, "rb") as f:
            pdf_data = f.read()
        pdf_b64 = base64.b64encode(pdf_data).decode()
        filename = f"{safe_name}_Fueling_Plan.pdf"

        # Send email via SendGrid
        print("=== SENDING EMAIL ===")
        mail = Mail(
            from_email=DELIVERY_EMAIL,
            to_emails=DELIVERY_EMAIL,
            subject=f"New Plan Ready - {athlete_name} ({sport})",
            plain_text_content=(
                f"New athlete fueling plan generated.\n\n"
                f"Athlete: {athlete_name}\n"
                f"Email: {athlete_email}\n"
                f"Sport: {sport}\n"
                f"Goal: {fields.get('Primary goal', 'Unknown')}\n\n"
                f"PDF attached. Review before forwarding to athlete."
            )
        )
        attachment = Attachment(
            FileContent(pdf_b64),
            FileName(filename),
            FileType("application/pdf"),
            Disposition("attachment")
        )
        mail.attachment = attachment
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(mail)
        print("=== EMAIL SENT SUCCESSFULLY ===")

        # Cleanup temp file
        os.unlink(tmp.name)

        return jsonify({"status": "success", "athlete": athlete_name}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
