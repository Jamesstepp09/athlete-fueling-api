from flask import Flask, request, send_file, jsonify
import tempfile
import os
import traceback
import json as json_lib
from pdf_generator import generate_plan

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/generate", methods=["POST"])
def generate():
    try:
        raw = request.get_data(as_text=False)
        print(f"=== RAW BODY LENGTH: {len(raw)} bytes ===")
        print(f"=== CONTENT TYPE: {request.content_type} ===")
        print(f"=== FIRST 500 CHARS: {raw[:500]} ===")

        try:
            raw_str = raw.decode('utf-8')
            athlete = json_lib.loads(raw_str)
        except Exception as e:
            print(f"=== PARSE ERROR: {e} ===")
            return jsonify({"error": f"Could not parse JSON body: {str(e)}", "body_length": len(raw), "first_100": str(raw[:100])}), 400

        if not athlete:
            return jsonify({"error": "Empty body"}), 400

        athlete_name = athlete.get("name", "Athlete").replace(" ", "_")
        tmp = tempfile.NamedTemporaryFile(
            suffix=".pdf",
            prefix=f"{athlete_name}_",
            delete=False
        )
        tmp.close()

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
