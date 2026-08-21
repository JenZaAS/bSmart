import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bselective_handler import get_item, list_items

HANDLER = Path(__file__).resolve().parents[1] / "bselective_handler.py"


SAMPLE_CLASS = """classdef SegyFile < handle
    %SEGYFILE Read SEG-Y data and headers.
    %   Minimal sample for bSelective tests.

    properties (Constant)
        DefaultFormat = "ieee-be"
    end

    properties (Access = public)
        FileName
        TraceHeaders = []
    end

    methods
        function obj = SegyFile(fileName)
            %SEGYFILE Construct a reader.
            obj.FileName = fileName;
        end

        function headers = loadHeaders(obj)
            %LOADHEADERS Load trace headers.
            headers = obj.TraceHeaders;
            if isempty(headers)
                headers = readTraceHeaders(obj.FileName);
            end
        end

        function value = get.TraceHeaders(obj)
            value = obj.TraceHeaders;
        end
    end
end
"""

CONTROL_FLOW_CLASS = """classdef ControlFlowExample
    methods
        function out = compute(obj, values)
            out = 0;
            if isempty(values)
                out = -1;
            else
                for idx = 1:numel(values)
                    if values(idx) > 0
                        out = out + values(idx);
                    end
                end
            end
            while out > 100
                out = out - 10;
            end
            out = out + 1;
        end

        function untouched(obj)
            disp('untouched');
        end
    end
end
"""


class BSelectiveHandlerTests(unittest.TestCase):
    def test_list_all_lists_extractable_parts_not_full_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "SegyFile.m"
            file.write_text(SAMPLE_CLASS, encoding="utf-8")
            result = list_items(file, "all")

        self.assertEqual(result["class"], "SegyFile")
        self.assertIn("DefaultFormat", [item["name"] for item in result["constants"]])
        self.assertIn("loadHeaders", [item["name"] for item in result["functions"]])
        self.assertIn("get.TraceHeaders", [item["name"] for item in result["getters"]])
        self.assertNotIn("source", result)

    def test_get_header_returns_only_help_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "SegyFile.m"
            file.write_text(SAMPLE_CLASS, encoding="utf-8")
            result = get_item(file, "header")

        self.assertEqual(result["help"][0], "SEGYFILE Read SEG-Y data and headers.")
        self.assertNotIn("function headers", json.dumps(result))

    def test_get_function_returns_only_target_function_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "SegyFile.m"
            file.write_text(SAMPLE_CLASS, encoding="utf-8")
            result = get_item(file, "function", "loadHeaders")

        self.assertIn("function headers = loadHeaders(obj)", result["source"])
        self.assertNotIn("function obj = SegyFile", result["source"])

    def test_get_function_handles_nested_control_flow_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "ControlFlowExample.m"
            file.write_text(CONTROL_FLOW_CLASS, encoding="utf-8")
            result = get_item(file, "function", "compute")

        source = result["source"]
        self.assertIn("if isempty(values)", source)
        self.assertIn("for idx = 1:numel(values)", source)
        self.assertIn("while out > 100", source)
        self.assertIn("out = out + 1;", source)
        self.assertNotIn("function untouched", source)
        self.assertGreater(result["end_line"], 15)


    def test_get_property_and_constant_property(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "SegyFile.m"
            file.write_text(SAMPLE_CLASS, encoding="utf-8")
            prop = get_item(file, "property", "TraceHeaders")
            const = get_item(file, "constant", "DefaultFormat")

        self.assertEqual(prop["properties"][0]["name"], "TraceHeaders")
        self.assertTrue(const["constant"]["constant"])

    def test_get_line_context_and_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "SegyFile.m"
            file.write_text(SAMPLE_CLASS, encoding="utf-8")
            context = get_item(file, "line", "22:1")
            refs = list_items(file, "refs", "TraceHeaders")

        self.assertEqual(context["start_line"], 21)
        self.assertEqual(context["end_line"], 23)
        self.assertGreaterEqual(len(refs["references"]), 3)

    def test_get_all_returns_full_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "SegyFile.m"
            file.write_text(SAMPLE_CLASS, encoding="utf-8")
            result = get_item(file, "all")

        self.assertIsInstance(result, str)
        self.assertIn("classdef SegyFile", result)

    def test_cli_uses_only_list_and_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "SegyFile.m"
            file.write_text(SAMPLE_CLASS, encoding="utf-8")
            list_out = subprocess.check_output([sys.executable, str(HANDLER), "list", str(file), "functions"], text=True)
            get_out = subprocess.check_output([sys.executable, str(HANDLER), "get", str(file), "constant", "DefaultFormat"], text=True)

        self.assertIn("loadHeaders", list_out)
        self.assertIn("DefaultFormat", get_out)


    def test_cli_list_defaults_to_compact_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "SegyFile.m"
            file.write_text(SAMPLE_CLASS, encoding="utf-8")
            list_out = subprocess.check_output([sys.executable, str(HANDLER), "list", str(file), "all"], text=True)

        self.assertIn("class: SegyFile", list_out)
        self.assertIn("functions:", list_out)
        self.assertIn("loadHeaders", list_out)
        self.assertIn("accessors:", list_out)
        self.assertNotIn('"file"', list_out)
        self.assertNotIn('"kind"', list_out)

    def test_cli_list_json_remains_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "SegyFile.m"
            file.write_text(SAMPLE_CLASS, encoding="utf-8")
            list_out = subprocess.check_output([sys.executable, str(HANDLER), "list", str(file), "all", "--format", "json", "--compact"], text=True)

        result = json.loads(list_out)
        self.assertEqual(result["class"], "SegyFile")
        self.assertEqual(result["kind"], "all")


if __name__ == "__main__":
    unittest.main()
