"""Tkinter GUI helper functions for widget generation."""

# import needed modules
from tkinter import *
from tkinter import messagebox


##############################################################################
####      GUI OBJECT GENERATION FUNCTIONS           ##########################
##############################################################################

def generate_drop_down(frame, options, callback_func=None, theme_config=None, width=None):
    """
    Generate a dropdown menu with optional theming.

    Args:
        frame: Parent frame for the dropdown
        options: List of options to display
        callback_func: Optional callback function when selection changes
        theme_config: Optional theme configuration dict. If provided, uses theme colors/fonts.
                     If None, uses default hardcoded values for backwards compatibility.

    Returns:
        Tuple of (dropdown_widget, string_var)
    """
    clicked_opt = StringVar()  # datatype of menu text_data
    try:
        clicked_opt.set(options[0])  # initial menu text_data (CAUSES ISSUES IF NO COM PORTS AVAILABLE)
    except Exception as e:
        clicked_opt.set("NA")
        options = ["NA"]

    def callback(*args):
        callback_func()

    if callback_func is not None:
        clicked_opt.trace("w", callback)

    drop = OptionMenu(frame, clicked_opt, *options)  # create drop down menu of years

    # Apply theming if provided, otherwise use defaults
    if width is None:
        width=15

    if theme_config is not None:
        drop.config(
            width=width,
            font=(theme_config["font"]["family"],
                  theme_config["font"]["size_s"]), # NOTE: not including `bold` here
            bg=theme_config["dark_3"],
            fg=theme_config["fg_light"]
        )
    else:
        # Backwards compatibility: use hardcoded defaults
        drop.config(width=15, font=('Arial', 8), bg="#2B2B2B", fg='#F8F8F2')

    return drop, clicked_opt


##############################################################################
####      PROMPT/ALERT FUNCTIONS           ###################################
##############################################################################

# promptYesNo: prompts the user for a yes or no response with a certain 'message' prompt
def promptYesNo(title, message):
    response = messagebox.askquestion(title, message)

    if response == "yes":
        return True
    else:
        return False


# alert_user: alerts the user with a prompt that flashes on the screen
#   kind can be of type {"error", "warning", and "info"}
def alert_user(title, message, kind):
    if kind not in ('error', 'warning', 'info'):
        raise ValueError('Unsupported alert kind.')

    show_method = getattr(messagebox, 'show{}'.format(kind))
    show_method(title, message)



