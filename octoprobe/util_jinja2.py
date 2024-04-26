import pathlib

import jinja2


class JinjaEnv:
    def __init__(self) -> None:
        jinja_search_path: list[str] = []
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(jinja_search_path),
            undefined=jinja2.StrictUndefined,
            extensions=["jinja2.ext.loopcontrols"],
        )

        self.env.filters["hexy"] = lambda value: f"0x{value:08X}"

    def render_file(self, filename: pathlib.Path, **kwargs) -> str:
        template = self.env.get_template(str(filename))
        rendered_text = template.render(kwargs=kwargs)
        return rendered_text

    def render_string(self, micropython_code: str, **kwargs) -> str:
        template = self.env.from_string(micropython_code)
        rendered_text = template.render(**kwargs)
        return rendered_text


_JINJA_ENV = JinjaEnv()

render = _JINJA_ENV.render_string
