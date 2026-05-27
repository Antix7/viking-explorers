import pygame as pg

# Implementation of a Button class, since pygame doesn't have one
class Button:
    def __init__(self, surface, x, y, width, height, base_color, hover_color, text_color, text, font, action):
        self.surface = surface
        self.rect = pg.Rect(x, y, width, height)
        self.base_color = base_color
        self.hover_color = hover_color
        self.current_color = base_color
        self.action = action
        self.text_surf, self.text_rect = font.render(text, text_color)
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
                return self.action()
        return None

    def draw(self):
        pg.draw.rect(self.surface, self.current_color, self.rect)
        self.surface.blit(self.text_surf, self.text_rect)

# A set of buttons that are used to toggle between different timewarp rates
class TimewarpControls:
    def __init__(self, surface, x, y, width, height, margin, base_color, hover_color, font, num_buttons):
        self.buttons = []
        r_arrow_char = '\u25B6'
        for i in range(num_buttons):
            def return_i(current_i=i):  # makes it so that the i value is saved when the function is defined, and not when it's called
                return current_i
            button = Button(surface, x+(width+margin)*i, y, width, height, base_color, hover_color,
                            "black", r_arrow_char*(i+1), font, return_i)
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