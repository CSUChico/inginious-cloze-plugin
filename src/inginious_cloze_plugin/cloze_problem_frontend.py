class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, task_fs):
        ClozeProblem.__init__(self, problemid, problem_content, translations, task_fs)
        DisplayableProblem.__init__(self, problemid, problem_content, translations, task_fs)

        # 🔥 IMPORTANT: keep the raw YAML around no matter what
        self._data = problem_content

    def _get_field(self, key, language, default=""):
        """
        Robustly fetch a field that might be:
          - a plain string
          - a dict of translations: {"en": "...", "fr": "..."}
        """
        data = getattr(self, "_data", None) or {}
        val = data.get(key)

        if isinstance(val, dict):
            # try exact language, then english, then any available
            if language in val and val[language]:
                return val[language]
            if "en" in val and val["en"]:
                return val["en"]
            for _, v in val.items():
                if v:
                    return v
            return default

        return val if val else default

    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        text = self._get_field("text", language, default="")
        label = self._get_field("name", language, default="Question")

        parts = []
        last = 0

        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)
            input_name = f"{pid}[{slot}]"
            parts.append(
                f'<input type="text" name="{html.escape(input_name)}" '
                f'class="form-control" '
                f'style="display:inline-block; width:12rem; margin:0 0.25rem;" />'
            )
            last = m.end()

        parts.append(html.escape(text[last:]))

        return f"""
<div class="panel panel-default">
  <div class="panel-heading">{html.escape(label)}</div>
  <div class="panel-body" style="line-height:2.2;">
    {''.join(parts)}
  </div>
</div>
"""
