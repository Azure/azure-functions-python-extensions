# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from abc import ABC

from azurefunctions.extensions.base import meta, sdkType, utils


class MockParamTypeInfo:
    def __init__(self, binding_name: str, pytype: type):
        self.binding_name = binding_name
        self.pytype = pytype


class MockFunction(ABC):
    def __init__(self, bindings: utils.Binding):
        self._bindings = bindings


class MockInitParams(utils.Binding):
    def __init__(self, name, direction, data_type, type, init_params, path=None):
        self.type = "blob"
        self.name = name
        self._direction = direction
        self._data_type = data_type
        self._dict = {
            "direction": self._direction,
            "dataType": self._data_type,
            "type": self.type,
        }
        self.init_params = init_params
        self.path = path


class TestUtils(unittest.TestCase):
    # Test Utils class
    def test_get_dict_repr_sdk(self):
        # Create mock blob
        meta._ConverterMeta._bindings = {"blob"}

        # Create test binding
        mock_blob = utils.Binding(
            name="client",
            direction=utils.BindingDirection.IN,
            data_type=None,
            type="blob",
        )

        # Create test input_types dict
        mock_input_types = {
            "client": MockParamTypeInfo(
                binding_name="blobTrigger", pytype=sdkType.SdkType
            )
        }

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr, logs = utils.get_raw_bindings(
            mock_indexed_functions, mock_input_types
        )
        self.assertEqual(
            dict_repr,
            [
                '{"direction": "IN", '
                '"type": "blob", '
                '"properties": '
                '{"SupportsDeferredBinding": true}}'
            ],
        )

        self.assertEqual(logs, {"client": {sdkType.SdkType: "True"}})

    def test_get_dict_repr_non_sdk(self):
        # Create mock blob
        meta._ConverterMeta._bindings = {"blob"}

        # Create test binding
        mock_blob = utils.Binding(
            name="blob",
            direction=utils.BindingDirection.IN,
            data_type=None,
            type="blob",
        )

        # Create test input_types dict
        mock_input_types = {
            "blob": MockParamTypeInfo(binding_name="blobTrigger", pytype=bytes)
        }

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr, logs = utils.get_raw_bindings(
            mock_indexed_functions, mock_input_types
        )
        self.assertEqual(
            dict_repr,
            [
                '{"direction": "IN", '
                '"type": "blob", '
                '"properties": '
                '{"SupportsDeferredBinding": false}}'
            ],
        )
        self.assertEqual(logs, {"blob": {bytes: "False"}})

    def test_get_dict_repr_binding_name_none(self):
        # Create mock blob
        meta._ConverterMeta._bindings = {"blob"}

        # Create test binding
        mock_blob = utils.Binding(
            name="blob",
            direction=utils.BindingDirection.IN,
            data_type=None,
            type="blob",
        )

        mock_http = utils.Binding(
            name="$return",
            direction=utils.BindingDirection.OUT,
            data_type=None,
            type="httpResponse",
        )

        # Create test input_types dict
        mock_input_types = {
            "blob": MockParamTypeInfo(binding_name="blobTrigger", pytype=bytes)
        }

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob, mock_http])

        dict_repr, logs = utils.get_raw_bindings(
            mock_indexed_functions, mock_input_types
        )
        self.assertEqual(
            dict_repr,
            [
                '{"direction": "IN", "type": "blob", '
                '"properties": {"SupportsDeferredBinding": false}}',
                '{"direction": "OUT", "type": "httpResponse", '
                '"properties": {"SupportsDeferredBinding": false}}',
            ],
        )
        self.assertEqual(logs, {"$return": {None: "False"}, "blob": {bytes: "False"}})

    def test_get_dict_repr_init_params(self):
        # Create mock blob
        meta._ConverterMeta._bindings = {"blob"}

        # Create test binding
        mock_blob = MockInitParams(
            name="client",
            direction=utils.BindingDirection.IN,
            data_type=None,
            type="blob",
            init_params=["test", "type", "direction"],
        )

        # Create test input_types dict
        mock_input_types = {
            "client": MockParamTypeInfo(
                binding_name="blobTrigger", pytype=sdkType.SdkType
            )
        }

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr, logs = utils.get_raw_bindings(
            mock_indexed_functions, mock_input_types
        )
        self.assertEqual(
            dict_repr,
            [
                '{"direction": "IN", '
                '"type": "blob", "properties": '
                '{"SupportsDeferredBinding": true}}'
            ],
        )

        self.assertEqual(logs, {"client": {sdkType.SdkType: "True"}})

    def test_get_dict_repr_clean_nones(self):
        # Create mock blob
        meta._ConverterMeta._bindings = {"blob"}

        # Create test binding
        mock_blob = MockInitParams(
            name="client",
            direction=utils.BindingDirection.IN,
            data_type=None,
            type="blob",
            path=None,
            init_params=["test", "type", "direction", "path"],
        )

        # Create test input_types dict
        mock_input_types = {
            "client": MockParamTypeInfo(
                binding_name="blobTrigger", pytype=sdkType.SdkType
            )
        }

        # Create test indexed_function
        mock_indexed_functions = MockFunction(bindings=[mock_blob])

        dict_repr, logs = utils.get_raw_bindings(
            mock_indexed_functions, mock_input_types
        )
        self.assertEqual(
            dict_repr,
            [
                '{"direction": "IN", '
                '"type": "blob", "properties": '
                '{"SupportsDeferredBinding": true}}'
            ],
        )

        self.assertEqual(logs, {"client": {sdkType.SdkType: "True"}})

    def test_binding_data_type(self):
        mock_blob = utils.Binding(
            name="blob",
            direction=utils.BindingDirection.IN,
            data_type=None,
            type="blob",
        )
        self.assertIsNone(mock_blob.data_type)

        mock_data_type = utils.Binding(
            name="blob",
            direction=utils.BindingDirection.IN,
            data_type=utils.DataType.STRING,
            type="blob",
        )
        self.assertEqual(mock_data_type.data_type, 1)

    def test_to_camel_case(self):
        test_str = ""
        self.assertRaises(ValueError, utils.to_camel_case, test_str)

        test_str = "1iAmNotAWord"
        self.assertRaises(ValueError, utils.to_camel_case, test_str)

        test_str = utils.to_camel_case("string_in_correct_format")
        self.assertEqual(test_str, "stringInCorrectFormat")

    def test_is_snake_case(self):
        test_str = "foo_bar_baz"
        self.assertTrue(utils.is_snake_case(test_str))

        test_str = "foo"
        self.assertFalse(utils.is_snake_case(test_str))

    def test_is_word(self):
        test_str = "1foo"
        self.assertFalse(utils.is_word(test_str))

        test_str = "foo_"
        self.assertFalse(utils.is_word(test_str))

        test_str = "foo"
        self.assertTrue(utils.is_word(test_str))

    def test_snake_case_to_camel_case_multi(self):
        self.assertEqual(utils.to_camel_case("data_type"), "dataType")

    def test_snake_case_to_camel_case_trailing_underscore(self):
        self.assertEqual(utils.to_camel_case("data_type_"), "dataType")

    def test_snake_case_to_camel_case_leading_underscore(self):
        self.assertEqual(utils.to_camel_case("_dataType"), "Datatype")

    def test_snake_case_to_camel_case_single(self):
        self.assertEqual(utils.to_camel_case("dataType"), "dataType")

    def test_snake_case_to_camel_case_empty_str(self):
        with self.assertRaises(ValueError) as err:
            utils.to_camel_case("")
        self.assertEqual(
            err.exception.args[0], "Please ensure arg name  is not " "empty!"
        )

    def test_snake_case_to_camel_case_none(self):
        with self.assertRaises(ValueError) as err:
            utils.to_camel_case(None)
        self.assertEqual(
            err.exception.args[0], "Please ensure arg name None is not " "empty!"
        )

    def test_snake_case_to_camel_case_not_one_word_nor_snake_case(self):
        with self.assertRaises(ValueError) as err:
            utils.to_camel_case("data-type")
        self.assertEqual(
            err.exception.args[0],
            "Please ensure data-type is a word or snake case "
            "string with underscore as separator.",
        )

    def test_is_snake_case_letters_only(self):
        self.assertTrue(utils.is_snake_case("dataType_foo"))

    def test_is_snake_case_lowercase_with_digit(self):
        self.assertTrue(utils.is_snake_case("data_type_233"))

    def test_is_snake_case_uppercase_with_digit(self):
        self.assertTrue(utils.is_snake_case("Data_Type_233"))

    def test_is_snake_case_leading_digit(self):
        self.assertFalse(utils.is_snake_case("233_Data_Type_233"))

    def test_is_snake_case_no_separator(self):
        self.assertFalse(utils.is_snake_case("DataType233"))

    def test_is_snake_case_invalid_separator(self):
        self.assertFalse(utils.is_snake_case("Data-Type-233"))

    def test_is_word_letters_only(self):
        self.assertTrue(utils.is_word("dataType"))

    def test_is_word_letters_with_digits(self):
        self.assertTrue(utils.is_word("dataType233"))

    def test_is_word_leading_digits(self):
        self.assertFalse(utils.is_word("233dataType"))

    def test_is_word_invalid_symbol(self):
        self.assertFalse(utils.is_word("233!dataType"))

    def test_clean_nones_none(self):
        self.assertEqual(utils.BuildDictMeta.clean_nones(None), None)

    def test_clean_nones_nested(self):
        self.assertEqual(
            utils.BuildDictMeta.clean_nones(
                {
                    "hello": None,
                    "hello2": [
                        "dummy1",
                        None,
                        "dummy2",
                        ["dummy3", None],
                        {"hello3": None},
                    ],
                    "hello4": {"dummy5": "pass1", "dummy6": None},
                }
            ),
            {
                "hello2": ["dummy1", "dummy2", ["dummy3"], {}],
                "hello4": {"dummy5": "pass1"},
            },  # NoQA
        )

    def test_add_to_dict_no_args(self):
        with self.assertRaises(ValueError) as err:

            @utils.BuildDictMeta.add_to_dict
            def dummy():
                pass

            dummy()

        self.assertEqual(
            err.exception.args[0],
            "dummy has no args. Please ensure func is an object " "method.",
        )

    def test_add_to_dict_valid(self):
        class TestDict:
            @utils.BuildDictMeta.add_to_dict
            def __init__(self, arg1, arg2, **kwargs):
                self.arg1 = arg1
                self.arg2 = arg2

        test_obj = TestDict("val1", "val2", dummy1="dummy1", dummy2="dummy2")

        self.assertCountEqual(
            getattr(test_obj, "init_params"),
            {"self", "arg1", "arg2", "kwargs", "dummy1", "dummy2"},
        )
        self.assertEqual(getattr(test_obj, "arg1", None), "val1")
        self.assertEqual(getattr(test_obj, "arg2", None), "val2")
        self.assertEqual(getattr(test_obj, "dummy1", None), "dummy1")
        self.assertEqual(getattr(test_obj, "dummy2", None), "dummy2")

    def test_add_to_dict_duplicate(self):
        class TestDict:
            @utils.BuildDictMeta.add_to_dict
            def __init__(self, arg1, arg2, **kwargs):
                self.arg1 = arg1
                self.arg2 = arg2
                self.arg3 = arg1

        test_obj = TestDict("val1", "val2", arg3="dummy1")

        self.assertCountEqual(
            getattr(test_obj, "init_params"), {"self", "arg1", "arg2", "kwargs", "arg3"}
        )
        self.assertEqual(getattr(test_obj, "arg1", None), "val1")
        self.assertEqual(getattr(test_obj, "arg2", None), "val2")
        self.assertEqual(getattr(test_obj, "arg3", None), "val1")

    def test_build_dict_meta(self):
        class TestBuildDict(metaclass=utils.BuildDictMeta):
            def __init__(self, arg1, arg2):
                pass

            def get_dict_repr(self):
                return {"hello": None, "world": ["dummy", None]}

        test_obj = TestBuildDict("val1", "val2")

        self.assertCountEqual(
            getattr(test_obj, "init_params"), {"self", "arg1", "arg2"}
        )
        self.assertEqual(test_obj.get_dict_repr(), {"world": ["dummy"]})
