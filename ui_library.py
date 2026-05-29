"""
This file serves as a library containing various configurable UI elements,
as well as functions for handling complex text rendering.
"""
import pygame as pg


# Theme class that stores color, font and screen size information
class Theme:
    def __init__(self, screen_width, screen_height, btn_base, btn_hover, btn_text, popup_bg, font, line_spacing):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.btn_base = btn_base
        self.btn_hover = btn_hover
        self.btn_text = btn_text
        self.popup_bg = popup_bg
        self.font = font
        self.line_spacing = line_spacing

# Implementation of a Button class, since pygame doesn't have one
class Button:
    def __init__(self, surface, rect, text, theme, callback):
        self.surface = surface
        self.rect = rect
        self.base_color = theme.btn_base
        self.hover_color = theme.btn_hover
        self.current_color = self.base_color
        self.callback = callback
        self.text_surf, self.text_rect = theme.font.render(text, theme.btn_text)
        self.text_rect.center = self.rect.center

    def update(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.hover_color
        else:
            self.current_color = self.base_color

    def update_alt(self, toggled):
        if toggled:
            self.current_color = self.hover_color
        else:
            self.current_color = self.base_color

    def handle_event(self, event, mouse_pos):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(mouse_pos):
                return self.callback()
        return None

    def draw(self):
        pg.draw.rect(self.surface, self.current_color, self.rect)
        self.surface.blit(self.text_surf, self.text_rect)

# A set of buttons that are used to toggle between different timewarp rates
class TimewarpControls:
    def __init__(self, surface, x, y, btn_width, btn_height, margin, theme, num_buttons):
        self.buttons = []
        self.theme = theme
        r_arrow_char = '\u25B6'
        for i in range(num_buttons):
            def return_i(current_i=i):  # makes it so that the i value is saved when the function is defined, and not when it's called
                return current_i
            btn_rect = pg.Rect(x + (btn_width + margin) * i, y, btn_width, btn_height)
            button = Button(surface, btn_rect, r_arrow_char * (i+1), theme, return_i)
            self.buttons.append(button)

    def update(self, **kwargs):
        for i, button in enumerate(self.buttons):
            button.update_alt(kwargs["timewarp_factor"] == i)

    def handle_event(self, event, mouse_pos):
        result = None
        for button in self.buttons:
            button_return = button.handle_event(event, mouse_pos)
            if button_return is not None:
                result = button_return
        return result

    def draw(self):
        for button in self.buttons:
            button.draw()

# Popup with a cancel/continue choice
class Popup:
    def __init__(self, surface, text, width, theme, callback):
        self.surface = surface
        self.theme = theme
        self.rendered_text = render_wrapped_text(text, theme.font, theme.btn_text, width, theme.line_spacing)
        text_rect = self.rendered_text.get_rect()
        self.rect = pg.Rect(0, 0, width+20, text_rect.height+70)
        self.rect.center = (theme.screen_width//2, theme.screen_height//2)
        self.shown = False
        def cont():
            self.shown = False
            callback()
        def cancel():
            self.shown = False
        btn_rect = pg.Rect(0, 0, 100, 30)
        btn_rect.bottomright = (self.rect.right-10, self.rect.bottom-10)
        continue_button = Button(surface, btn_rect, "Continue", theme, cont)
        btn_rect = pg.Rect(0, 0, 100, 30)
        btn_rect.bottomright = (self.rect.right - 120, self.rect.bottom - 10)
        cancel_button = Button(surface, btn_rect, "Cancel", theme, cancel)
        self.buttons = [continue_button, cancel_button]

    def update(self, mouse_pos):
        if self.shown:
            for button in self.buttons:
                button.update(mouse_pos)

    def handle_event(self, event, mouse_pos):
        if self.shown:
            for button in self.buttons:
                button.handle_event(event, mouse_pos)

    def draw(self):
        if self.shown:
            pg.draw.rect(self.surface, self.theme.popup_bg, self.rect)
            self.surface.blit(self.rendered_text, (self.rect.x+10, self.rect.y+10))
            for button in self.buttons:
                button.draw()


# Renders a block of text wrapped to a specific width
def render_wrapped_text(text, font, color, max_width, line_spacing):
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        _, test_rect = font.render(test_line, color)
        test_width = test_rect.width
        if test_width <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    rendered_lines = [font.render(line, color)[0] for line in lines]
    line_height = rendered_lines[0].get_rect().height + line_spacing
    total_height = line_height * len(rendered_lines)
    total_width = max(surf.get_width() for surf in rendered_lines)
    result = pg.Surface((total_width, total_height), pg.SRCALPHA)
    for i, line_surf in enumerate(rendered_lines):
        result.blit(line_surf, (0, i * line_height))
    return result

# Renders multiple paragraphs of text at once
def render_paragraphs(text, font, color, max_width, line_spacing, par_spacing):
    paragraphs = text.split("\n")
    rendered_paragraphs = []
    for paragraph in paragraphs:
        rendered_paragraphs.append(render_wrapped_text(paragraph, font, color, max_width, line_spacing))
    total_height = sum(p.get_height() for p in rendered_paragraphs) + par_spacing*(len(paragraphs)-1)
    total_width = max(p.get_width() for p in rendered_paragraphs)
    result = pg.Surface((total_width, total_height), pg.SRCALPHA)
    current_y = 0
    for surface in rendered_paragraphs:
        result.blit(surface, (0, current_y))
        current_y += surface.get_height() + par_spacing
    return result
