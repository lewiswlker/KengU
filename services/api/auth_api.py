from flask import Blueprint, request, jsonify
from auth import verify_hku_credentials
from dao import UserDAO

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/hku-auth", methods=["POST"])
def hku_auth():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    result = verify_hku_credentials(
        email=email,
        password=password,
        headless=True,
        verbose=True
    )
    return jsonify(result)

@auth_bp.route("/user/check-and-create", methods=["POST"])
def check_and_create_user():
    data = request.json
    email = data.get("email")
    
    if not (email.endswith("@connect.hku.hk") or email.endswith("@hku.hk")):
        return jsonify({
            "success": False,
            "message": "Please use HKU email"
        }), 400


    user_dao = UserDAO()

    user = user_dao.find_by_email(email)
    if not user:
        try:
            new_user_id = user_dao.insert_user(user_email=email, pwd="")
            user = user_dao.find_by_id(new_user_id)
            print(f"Add successfully:email={email}, ID={new_user_id}")
        except RuntimeError as e:
            return jsonify({
                "success": False,
                "message": f"Fail to add in users table:{str(e)}"
            }), 500

    return jsonify({
        "success": True,
        "message": "user store successfully",
        "data": {
            "userId": user["id"],
            "userEmail": user["user_email"]
        }
    })