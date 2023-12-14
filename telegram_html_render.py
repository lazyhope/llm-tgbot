import html
import re
import textwrap

# from typing import override
from mistletoe import block_token, span_token
from mistletoe.html_renderer import HtmlRenderer


class Spoiler(span_token.SpanToken):
    """
    Spoiler token. ("||some text||")
    This is an inline token. Its children are inline (span) tokens.
    """

    pattern = re.compile(r"(?<!\\)(?:\\\\)*\|\|(.+?)\|\|", re.DOTALL)


class Underline(span_token.SpanToken):
    """
    Underline token. ("__some text__")
    This is an inline token. Its children are inline (span) tokens.
    """

    pattern = re.compile(r"(?<!\\)(?:\\\\)*__(.+?)__(?!_)", re.DOTALL)


class TelegramHtmlRenderer(HtmlRenderer):
    def __init__(self, *extras, **kwargs):
        super().__init__(Spoiler, Underline, *extras, **kwargs)
        self.unordered_marks = ["•", "◦", "▪"]  # Replacement for unordered item mark
        self.leader_i = 0  # Track list item level
        self.heading_mark = "▎"  # For representing headings

    # @override
    def render_image(self, token: span_token.Image) -> str:
        """Replace image tags with link or emoji tags."""
        inner = self.render_inner(token)

        emoji_match = re.match(r"tg://emoji\?id=(\d+)", token.src)
        if emoji_match is not None:
            emoji_id = emoji_match.group(1)
            return f'<tg-emoji emoji-id="{emoji_id}">{inner}</tg-emoji>'

        template = '<a href="{src}"{title}>{inner}</a>'
        src = self.escape_url(token.src)
        if token.title:
            title = ' title="{}"'.format(html.escape(token.title))
        else:
            title = ""
        return template.format(src=src, title=title, inner=inner)

    # @override
    def render_heading(self, token: block_token.Heading) -> str:
        """HTML headings not yet supported in Telegram."""
        template = "{level} <b>{inner}</b>"
        level = self.heading_mark * token.level
        inner = self.render_inner(token)
        return template.format(level=level, inner=inner)

    # @override
    def render_paragraph(self, token: block_token.Paragraph) -> str:
        """HTML paragraphs not yet supported in Telegram"""
        return "{}".format(self.render_inner(token))

    # @override
    def render_list(self, token: block_token.List) -> str:
        """HTML lists not yet supported in Telegram"""
        return f"\n{self.render_inner(token)}\n"

    # @override
    def render_list_item(self, token: block_token.ListItem) -> str:
        """HTML list items not yet supported in Telegram"""
        indentation = len(token.leader) + 1
        leader = token.leader
        if token.leader in ["+", "-", "*"]:
            leader = self.unordered_marks[min(self.leader_i, 2)]

        self.leader_i += 1
        first_item_lines = (
            self.render(token.children[0]).strip("\n").splitlines()
            if token.children
            else ""
        )

        first_line = leader + " " + first_item_lines[0]
        following_lines = first_item_lines[1:] + [
            child_line if not child_line.isspace() else ""
            for child in token.children[1:]
            for child_line in self.render(child).strip("\n").splitlines()
        ]
        self.leader_i -= 1

        following_line_prefix = " " * indentation
        following_block = textwrap.indent(
            "\n".join(following_lines), following_line_prefix
        )

        return f"{first_line}\n{following_block}"

    def render_spoiler(self, token: Spoiler) -> str:
        """Telegram spoiler tag"""
        template = "<tg-spoiler>{}</tg-spoiler>"
        return template.format(self.render_inner(token))

    def render_underline(self, token: Underline) -> str:
        """Telegram underline tag"""
        template = "<u>{}</u>"
        return template.format(self.render_inner(token))
