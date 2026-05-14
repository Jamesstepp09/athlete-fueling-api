from flask import Flask, request, send_file, jsonify
import tempfile
import os
import traceback
from pdf_generator import generate_plan

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/generate", methods=["POST"])
def generate():
    try:
        athlete = request.get_json()
        if not athlete:
            return jsonify({"error": "No JSON body received"}), 400

        # Write PDF to a temp file
        athlete_name = athlete.get("name", "Athlete").replace(" ", "_")
        tmp = tempfile.NamedTemporaryFile(
            suffix=".pdf",
            prefix=f"{athlete_name}_",
            delete=False
        )
        tmp.close()

        # Override output path to temp file
        athlete["_output_path"] = tmp.name
        generate_plan(athlete, output_path=tmp.name)

        return send_file(
            tmp.name,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{athlete_name}_Fueling_Plan.pdf"
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
