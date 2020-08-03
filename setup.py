# PySchemeTranspiler, Transpile simple Python to Scheme(Racket)
# Copyright (C) 2020  Rubin Raithel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import setuptools

setuptools.setup(
    name="PySchemeTranspiler",
    version="1.0",
    author="Rubin Raithel",
    author_email="dev@rubinraithel.de",
    description="Transpile simple Python to Scheme(Racket)",
    url="https://github.com/Coronon/PySchemeTranspiler",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    entry_points = {
        "console_scripts": ['pystranspile = pyschemetranspiler.run:main']
        },
)
