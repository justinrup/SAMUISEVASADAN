import os
import secrets
from flask import Flask, send_from_directory, request, jsonify, session, redirect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# Secret key for admin session
SECRET_FILE = os.path.join(BASE_DIR, ".session_secret")

if os.path.exists(SECRET_FILE):
    with open(SECRET_FILE, "r") as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(SECRET_FILE, "w") as f:
        f.write(app.secret_key)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def get_admin_password():
    password_file = os.path.join(BASE_DIR, ".admin_password")

    if os.path.exists(password_file):
        try:
            with open(password_file, "r") as f:
                password = f.read().strip()
            if password:
                return password
        except Exception:
            pass

    return os.environ.get("ADMIN_PASSWORD", "").strip()


def admin_logged_in():
    return session.get("sss_admin_logged_in") is True


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/admin-login.html")
@app.route("/admin.html")
def admin_login_page():
    return send_from_directory(BASE_DIR, "admin-login.html")


@app.route("/api/admin-login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if username != "admin":
        return jsonify({
            "ok": False,
            "message": "Invalid Admin Name or Password"
        }), 401

    saved_password = get_admin_password()

    if saved_password and password == saved_password:
        session.clear()
        session["sss_admin_logged_in"] = True
        return jsonify({
            "ok": True,
            "message": "Login successful"
        })

    return jsonify({
        "ok": False,
        "message": "Invalid Admin Name or Password"
    }), 401



@app.route("/api/admin-login-settings", methods=["POST"])
def admin_login_settings():
    if not admin_logged_in():
        return jsonify({
            "ok": False,
            "message": "Admin login required"
        }), 401

    data = request.get_json(silent=True) or {}

    current_password = str(data.get("currentPassword", ""))
    new_username = str(data.get("username", "")).strip()
    new_password = str(data.get("newPassword", ""))

    if not current_password or not new_username or not new_password:
        return jsonify({
            "ok": False,
            "message": "All fields are required"
        }), 400

    if current_password != get_admin_password():
        return jsonify({
            "ok": False,
            "message": "Current password is incorrect"
        }), 401

    if new_username != "admin":
        return jsonify({
            "ok": False,
            "message": "For this project the admin username must remain: admin"
        }), 400

    if len(new_password) < 6:
        return jsonify({
            "ok": False,
            "message": "New password must be at least 6 characters"
        }), 400

    password_file = os.path.join(BASE_DIR, ".admin_password")

    try:
        with open(password_file, "w") as f:
            f.write(new_password)

        return jsonify({
            "ok": True,
            "message": "Login settings updated successfully"
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": "Could not save password"
        }), 500


@app.route("/api/admin-status")
def admin_status():
    return jsonify({
        "loggedIn": admin_logged_in()
    })


@app.route("/api/admin-logout", methods=["POST"])
def admin_logout():
    session.clear()
    return jsonify({
        "ok": True
    })


@app.route("/admin-dashboard.html")
def admin_dashboard():
    if not admin_logged_in():
        return redirect("/admin-login.html")

    return send_from_directory(BASE_DIR, "admin-dashboard.html")


@app.route("/<path:path>")
def files(path):
    # Never expose hidden/security files
    if path.startswith(".") or "/." in path:
        return "Not Found", 404

    # Never allow dashboard through the catch-all route
    if path == "admin-dashboard.html":
        if not admin_logged_in():
            return redirect("/admin-login.html")

    return send_from_directory(BASE_DIR, path)


# ================= SITE CONTENT MANAGEMENT =================

SITE_CONTENT_FILE = os.path.join(BASE_DIR, "site_content.json")

def get_site_content():
    default = {
        "services": {
            "title": "Healthcare Services",
            "description": "Quality healthcare services for our patients.",
            "items": [],
            "published": False
        },
        "doctors": {
            "title": "Our Doctors",
            "description": "Meet our doctors and specialists.",
            "items": [],
            "published": False
        },
        "facilities": {
            "title": "Facilities",
            "description": "Explore our available facilities.",
            "items": [],
            "published": False
        }
    }

    try:
        if os.path.exists(SITE_CONTENT_FILE):
            with open(SITE_CONTENT_FILE, "r", encoding="utf-8") as f:
                saved = __import__("json").load(f)

            for key in default:
                if key in saved:
                    default[key].update(saved[key])

    except Exception:
        pass

    return default


def save_site_content(data):
    import json
    with open(SITE_CONTENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/api/site-content/<section>")
def get_public_site_content(section):
    if section not in ("services", "doctors", "facilities"):
        return jsonify({"ok": False, "message": "Invalid section"}), 404

    data = get_site_content()
    return jsonify({
        "ok": True,
        "section": section,
        "content": data[section]
    })


@app.route("/api/admin/site-content/<section>", methods=["GET"])
def get_admin_site_content(section):
    if not admin_logged_in():
        return jsonify({
            "ok": False,
            "message": "Admin login required"
        }), 401

    if section not in ("services", "doctors", "facilities"):
        return jsonify({"ok": False, "message": "Invalid section"}), 404

    data = get_site_content()

    return jsonify({
        "ok": True,
        "section": section,
        "content": data[section]
    })


@app.route("/api/admin/site-content/<section>", methods=["POST"])
def save_admin_site_content(section):
    if not admin_logged_in():
        return jsonify({
            "ok": False,
            "message": "Admin login required"
        }), 401

    if section not in ("services", "doctors", "facilities"):
        return jsonify({"ok": False, "message": "Invalid section"}), 404

    incoming = request.get_json(silent=True) or {}

    data = get_site_content()

    if "title" in incoming:
        data[section]["title"] = str(incoming["title"]).strip()

    if "description" in incoming:
        data[section]["description"] = str(incoming["description"]).strip()

    if isinstance(incoming.get("items"), list):
        data[section]["items"] = incoming["items"]

    if "published" in incoming:
        data[section]["published"] = bool(incoming["published"])

    save_site_content(data)

    return jsonify({
        "ok": True,
        "message": "Content saved successfully",
        "content": data[section]
    })


# ============================================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False)
