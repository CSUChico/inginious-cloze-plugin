from flask import Blueprint

bp = Blueprint("cloze_editor", __name__, url_prefix="/plugins/cloze")

@bp.route("/preview")
def preview():
    return "preview"
