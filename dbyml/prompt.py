import re
from typing import Any, Callable, Optional

import prompt_toolkit
from prompt_toolkit import prompt
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.styles import BaseStyle
from prompt_toolkit.widgets import CheckboxList, Label


def checkbox_list(
    title: str = "",
    values: list = [],
    style: Optional[BaseStyle] = None,
    async_: bool = False,
) -> Any:
    # Add exit key binding.
    bindings = KeyBindings()

    @bindings.add("c-d")
    def exit_(event: KeyPressEvent) -> None:
        """
        Pressing Ctrl-d will exit the user interface.
        """
        event.app.exit()

    @bindings.add("enter", eager=True)
    def exit_with_value(event: KeyPressEvent) -> Optional[list]:  # type: ignore
        """
        Pressing Enter will exit the user interface returning the selected values.
        """
        event.app.exit(result=checkbox.current_values)

    @bindings.add("right")
    def _handle_enter(event: KeyPressEvent) -> None:
        """Select the current value.

        Pressing Right arrow (->) to select the option for the position where the cursor is currently located.
        Press again at the same position to remove it as an option.

        Args:
            event ([type]): [description]
        """
        if checkbox.multiple_selection:
            val = checkbox.values[checkbox._selected_index][0]
            if val in checkbox.current_values:
                checkbox.current_values.remove(val)
            else:
                checkbox.current_values.append(val)
        else:
            checkbox.current_value = checkbox.values[checkbox._selected_index][0]

    checkbox = CheckboxList(values)
    application: Application = Application(
        layout=Layout(HSplit([Label(title), checkbox])),
        key_bindings=merge_key_bindings([load_key_bindings(), bindings]),
        # key_bindings=merge_key_bindings(bindings),
        mouse_support=True,
        style=style,
        full_screen=False,
        erase_when_done=True,
    )

    if async_:
        return application.run_async()
    else:
        return application.run()


class Prompt:
    def get_str_data(
        self,
        msg: str,
        validate_msg: str = "",
        validator: Callable = None,
        default: Optional[str] = None,
    ) -> str:
        """Get text from user input.

        Validate input value by user with validator.
        When the validator is not set, only check the value length is less than max.

        Args:
            msg (str): The text displayed as user prompt.
            validate_msg (str, optional): The text displayed when input value violates the validation. Defaults to "".
            validator (Callable, optional): A method called for validation. Defaults to None.
            default (Optional[str], optional): Default value used when user input is empty.

        Returns:
            str: The value entered by user.
        """
        if validator is None:
            validator = Validator.common_str
        if validate_msg == "":
            validate_msg = "The max length is 256."

        if default is not None:
            msg = f"{msg} Default: {default}"

        return self.input_prompt(
            msg=msg,
            validate_while_typing=True,
            validate_msg=validate_msg,
            _validator=validator,
        ).strip()

    def get_dict_data(
        self,
        msg: str,
        validate_msg: str = "",
        validator: Callable = None,
        continue_msg: str = "",
        default: Optional[str] = None,
    ) -> dict:
        """Get text from user input, separate its to key and value.

        Validate input value by user with validator.
        When the validator is not set, checks that the value length is less than max
        and that the value contains a semicolon in order to separate to dict.

        A key-value is set, the user will be asked if wants to continue with the setting of the pair up to 100.

        Args:
            msg (str): The text displayed as user prompt.
            validate_msg (str, optional): The text displayed when input value violates the validation. Defaults to "".
            validator (Callable, optional): A method called for validation. Defaults to None.
            continue_msg (str, optional): The text displayed after one key-value pair is set. Defaults to "".
            default (Optional[str], optional): Default value used when user input is empty.

        Returns:
            dict: The key and value entered by user.
        """
        arg = {}
        ask = "yes"
        num = 1

        if continue_msg == "":
            continue_msg = "Do you continue? (y/n) :"

        if validator is None:
            validator = Validator.common_dict

        if default is not None:
            msg = f"{msg} Default: {default}"

        # Continue with the prompt up to 100.
        while re.search("y|yes", ask.lower()) and num <= 100:
            ret = self.input_prompt(
                msg=f"{msg} This is {num}th time input.",
                validate_while_typing=True,
                validate_msg=validate_msg,
                _validator=validator,
            )
            d = ret.split(":")
            arg[d[0].strip()] = d[1].strip()
            ask = self.input_prompt(
                f"{continue_msg} (y/n) :",
                user_prompt=False,
                validate_while_typing=False,
                _validator=None,
            )
            num += 1
        return arg

    def get_properties(self) -> list:
        """Get values from selected options.

        Returns:
            list: List of values corresponding to the selected options.
        """
        return checkbox_list(
            title=(
                "Choose fields you want to set interactively."
                "Right arrow (->) to check the field then press Enter.\n"
            ),
            values=[
                ("build_args", "Build_args"),
                ("label", "Label"),
                ("registry", "Registry"),
            ],
        )

    def input_prompt(
        self,
        msg: str,
        user_prompt: bool = True,
        validate_while_typing: bool = False,
        validate_msg: str = "",
        _validator: Callable[[str], bool] = None,
    ) -> str:
        if user_prompt is True:
            msg = f"{msg}\n> "

        if _validator is not None:
            validator = prompt_toolkit.validation.Validator.from_callable(
                _validator,
                error_message=validate_msg,
                move_cursor_to_end=True,
            )
            return prompt(
                msg,
                validator=validator,
                validate_while_typing=validate_while_typing,
                enable_history_search=True,
            )
        else:
            return prompt(msg)

    def interactive_prompt(self) -> dict:
        """Interactively set fields to config.

        Returns:
            dict: The values of fields
        """
        # Default field keys and values.
        ret = {
            "name": "",
            "tag": "latest",
            "path": ".",
            "build_args": {},
            "label": {},
            "username": "",
            "password": "",
            "host": "registry",
            "port": 5000,
            "set_registry": False,
        }

        print("-" * 20 + f"{'Interactive prompt start.':^30}" + "-" * 20)
        print(
            "Type values you want to set then press Enter. To use default value, press Enter with no input."
        )
        print("-" * 70)

        ret["name"] = self.get_str_data(
            "Input the image name to be built from your Dockerfile.",
            "Image name cannot be empty or contain `:`.",
            Validator.common_text,
        )
        ret["tag"] = self.get_str_data(
            "Input the image tag to be built from your Dockerfile.",
            "Tag cannot contain `:`.",
            Validator.image_tag,
            "latest",
        )

        tmp = self.get_str_data(
            "Input path to the directory where your Dockerfile exists.", default="."
        )

        if tmp != "":
            ret["path"] = tmp

        options = self.get_properties()
        if "build_args" in options:
            ret["build_args"] = self.get_dict_data(
                "Input the build_args.",
                "The format muse be 'key:value'.",
                continue_msg="Do you set more build_args ?",
            )
        if "label" in options:
            ret["label"] = self.get_dict_data(
                "Input the label.",
                "The format muse be 'key:value'.",
                continue_msg="Do you set more label ?",
            )
        if "registry" in options:
            # print(skip_prompt)
            ret["set_registry"] = True
            ret["username"] = self.get_str_data(
                "Input the username of registry.", default="None"
            )
            ret["password"] = self.get_str_data(
                "Input the password of registry.", default="None"
            )
            ret["host"] = self.get_str_data(
                "Input the registry hostname or IP address."
            )

            tmp = self.get_str_data(
                "Input the registry port.",
                "The port is valid up to 5 digits.",
                Validator.registry_port,
                default="5000",
            )
            if tmp != "":
                ret["port"] = int(tmp)

        return self.word_check(ret)

    def word_check(self, _dict: dict) -> dict:
        """Use quotes to keys and values containing the specific patterns."""
        pattern = r"^.*(\.|\s).*$"

        for k, v in _dict.copy().items():
            if isinstance(v, dict):
                self.word_check(v)
            elif isinstance(v, str):
                if re.search(pattern, k):
                    new_key = f'"{k}"'
                    _dict[new_key] = _dict.pop(k)
                    if re.search(pattern, v):
                        _dict[new_key] = f'"{v}"'
                else:
                    if re.search(pattern, v):
                        _dict[k] = f'"{v}"'
            else:
                pass
        return _dict


class Validator:
    """Class for validating input values from user."""

    max_count = 256
    max_port_digit = 6

    @staticmethod
    def common_text(text: str) -> bool:
        """Common validator for checking the text.

        Args:
            text (str): Input text.
            empty_ok (bool, optional): Whether to accept empty string. Defaults to False.

        Returns:
            bool: True if validation is OK, False otherwise
        """
        return ":" not in text and text != "" and len(text) < Validator.max_count

    @staticmethod
    def common_str(text: str) -> bool:
        """Common validator for checking the str.

        Args:
            text (str): Input text.

        Returns:
            bool: True if validation is OK, False otherwise
        """
        return len(text) < Validator.max_count

    @staticmethod
    def common_dict(text: str) -> bool:
        """Common validator for checking text can be interpreted as dict.

        Args:
            text (str): Input text.

        Returns:
            bool: True if validation is OK, False otherwise
        """
        comp = text.split(":")
        return len(comp) == 2 and comp[0] != "" and len(text) < Validator.max_count

    @staticmethod
    def registry_port(text: str) -> bool:
        """A validator for checking port is in range.

        Args:
            text (str): Input text.

        Returns:
            bool: True if validation is OK, False otherwise
        """
        if len(text) == 0:
            return True
        else:
            return len(text) < Validator.max_port_digit and text.isdigit()

    @staticmethod
    def image_tag(text: str) -> bool:
        """A validator for checking the tag is valid.

        Args:
            text (str): Input text.

        Returns:
            bool: True if validation is OK, False otherwise
        """
        return ":" not in text and len(text) < Validator.max_count


if __name__ == "__main__":
    p = Prompt()
    p.interactive_prompt()
