"""
This file serves as a library containing various configurable UI elements,
as well as functions for handling complex text rendering.
"""
import pygame as pg


# Theme class that stores color, font and screen size information
class Theme:
    def __init__(self, screen_width, screen_height, btn_base, btn_hover, btn_text, popup_bg, font, line_spacing, par_spacing):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.btn_base = btn_base
        self.btn_hover = btn_hover
        self.btn_text = btn_text
        self.popup_bg = popup_bg
        self.font = font
        self.line_spacing = line_spacing
        self.par_spacing = par_spacing

# Implementation of a Button class, since pygame doesn't have one
class Button:
    def __init__(self, surface, rect, text, theme, callback):
        self.surface = surface
        self.theme = theme
        self.rect = rect
        self.base_color = theme.btn_base
        self.hover_color = theme.btn_hover
        self.current_color = self.base_color
        self.callback = callback
        self.text_surf, self.text_rect = pg.Surface((0, 0)), pg.Rect(0, 0, 0, 0)
        self.set_text(text)

    def set_rect(self, new_rect):
        self.rect = new_rect
        self.text_rect.center = self.rect.center

    def set_text(self, new_text):
        self.text_surf, self.text_rect = self.theme.font.render(new_text, self.theme.btn_text)
        self.text_rect.center = self.rect.center
        if has_hanging_letters(new_text):
            self.text_rect.y += self.text_rect.height * 0.15
        if 'i' in new_text:
            self.text_rect.y -= self.text_rect.height * 0.05

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

# Popup box with customizable action buttons
class Popup:
    def __init__(self, surface, text, width, theme, btn1_text, btn1_callback, btn2_text, btn2_callback, one_button=False):
        self.surface = surface
        self.theme = theme
        self.width = width
        self.one_button = one_button
        self.rendered_text = pg.Surface((0, 0))
        self.rect = pg.Rect(0, 0, 0, 0)
        def cont():
            self.shown = False
            btn2_callback()
        def cancel():
            self.shown = False
            btn1_callback()
        btn_rect = pg.Rect(0, 0, 100, 30)
        continue_button = Button(surface, btn_rect, btn2_text, theme, cont)
        if not one_button:
            cancel_button = Button(surface, btn_rect, btn1_text, theme, cancel)
            self.buttons = [continue_button, cancel_button]
        else:
            self.buttons = [continue_button]
        self.set_text(text)
        self.shown = False

    def set_text(self, new_text):
        self.rendered_text = render_paragraphs(new_text, self.theme.font,
                self.theme.btn_text, self.width, self.theme.line_spacing, self.theme.par_spacing)
        text_rect = self.rendered_text.get_rect()
        self.rect = pg.Rect(0, 0, self.width + 40, text_rect.height + 90)
        self.rect.center = (self.theme.screen_width // 2, self.theme.screen_height // 2)
        btn_rect = pg.Rect(0, 0, 100, 30)
        btn_rect.bottomright = (self.rect.right - 20, self.rect.bottom - 20)
        self.buttons[0].set_rect(btn_rect)
        if not self.one_button:
            btn_rect = pg.Rect(0, 0, 100, 30)
            btn_rect.bottomright = (self.rect.right - 130, self.rect.bottom - 20)
            self.buttons[1].set_rect(btn_rect)

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
            self.surface.blit(self.rendered_text, (self.rect.x+20, self.rect.y+20))
            for button in self.buttons:
                button.draw()


# Checks if test contains hanging letters, used for alignment
def has_hanging_letters(text):
    hanging_letters = list("Qqypgj")
    result = False
    for letter in hanging_letters:
        if letter in text:
            result = True
    return result

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
    max_line_height = max(l.get_rect().height for l in rendered_lines)
    line_height = max_line_height + line_spacing
    total_height = line_height * len(rendered_lines)
    total_width = max(surf.get_width() for surf in rendered_lines)
    result = pg.Surface((total_width, total_height), pg.SRCALPHA)
    c = pg.Color(color)
    result.fill((c.r, c.g, c.b, 0))
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
