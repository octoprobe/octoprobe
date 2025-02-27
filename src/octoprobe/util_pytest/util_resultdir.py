from __future__ import annotations

import logging
import os
import pathlib

logger = logging.getLogger(__file__)


class ResultFile:
    """
    A ResultFile is a testresult stored in a file.
    """

    def __init__(
        self,
        resultsdir: ResultsDir,
        filename: str,
        sub_directory: str | None = None,
    ):
        assert isinstance(resultsdir, ResultsDir)
        assert isinstance(filename, str)
        assert isinstance(sub_directory, str | None)
        self._resultsdir = resultsdir
        self._filename = ResultFile.slugify(filename)
        self._sub_directory = sub_directory

    @staticmethod
    def slugify(filename: str) -> str:
        """
        Replace invalid characters in a filename.
        Example: 2021-09-30 20:10.12.501582 -> 2021-09-30_20.10.12.501582
        """
        for a, b in (
            ("$", "_"),
            (",", "_"),
            ("/", "_"),
            ("\\", "_"),
            (" ", "_"),
            (":", "."),
        ):
            filename = filename.replace(a, b)
        return filename

    @staticmethod
    def nodeid_2_path(nodeid: str) -> str:
        """
        Example nodeids:
        test function:
            tests/test_simple.py::test_i2c[pico-1722-POTPOURRY_3f31-DAQ_SALEAE_1331]
        class with test method:
            tests/test_simple.py::Test::test_a
        Returns a relative path
        """
        for s, r in (
            (".py::", "/"),
            ("::", "/"),
            ("*", "+"),
        ):
            nodeid = nodeid.replace(s, r)
        # translation: dict[str, str] = {
        #     "*": "+",
        #     # "[": "_",
        #     # "=": "",
        #     # "]": "",
        #     # "*": "+",
        # }
        # path = path.translate(str.maketrans(translation))
        return nodeid

    @property
    def resultsdir(self) -> ResultsDir:
        return self._resultsdir

    @property
    def relative(self) -> str:
        """
        The filename relative to the output directory.
        """
        if self._sub_directory is not None:
            return f"{self._resultsdir.directory_test_relative}/{self.slugify(self._sub_directory)}/{self._filename}"
        return f"{self._resultsdir.directory_test_relative}/{self._filename}"

    @property
    def filename(self) -> pathlib.Path:
        """
        The absolute file name.
        Should be used to safe the file
        """
        _file = (self._resultsdir.directory_top / self.relative).resolve()
        _file.parent.mkdir(parents=True, exist_ok=True)
        return _file

    def make_unique(self, i=0) -> None:
        """Make filename unique by adding a number to it if it already exists"""
        if self.filename.is_file():
            root, ext = os.path.splitext(self._filename)
            self._filename = f"{root}{i}{ext}"
            self.make_unique(i=i + 1)


class ResultsDir:
    """
    This specifies the directory where the artifacts of the current tests will be written
    """

    def __init__(
        self,
        directory_top: pathlib.Path,
        test_name: str,
        test_nodeid: str,
    ):
        assert isinstance(directory_top, pathlib.Path)
        assert isinstance(test_name, str)
        assert isinstance(test_nodeid, str)
        self.test_name = test_name
        """
        For example: tests/test_simple.py::test_i2c[pico-1722-POTPOURRY_3f31-DAQ_SALEAE_1331]
        """
        self.test_nodeid = test_nodeid
        """
        For example: test_i2c[pico-1722-POTPOURRY_3f31-DAQ_SALEAE_1331]
        """
        self.directory_top = directory_top
        """
        The top directory of the testresults
        """
        self.directory_test_relative = ResultFile.nodeid_2_path(nodeid=test_nodeid)
        """
        The relative path (str)
        """
        self.directory_test = directory_top / self.directory_test_relative
        """
        The absolute directory for this test
        """
        self.directory_test.mkdir(parents=True, exist_ok=True)

    def __call__(self, filename: str, sub_directory: str | None = None) -> ResultFile:
        return ResultFile(
            resultsdir=self,
            filename=filename,
            sub_directory=sub_directory,
        )

    # def file(self, filename: str, sub_directory: str = None) -> ResultFile:
    #     return ResultFile(
    #         resultsdir=self,
    #         filename=filename,
    #         sub_directory=sub_directory,
    #     )
