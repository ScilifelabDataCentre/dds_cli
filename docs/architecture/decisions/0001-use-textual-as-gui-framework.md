# 1. Use Textual as GUI Framework

Date: Spring 2025

## Status

Accepted

## Context

In order to allow users to take advantage of the DDS functionality without requiring the use of a terminal / command line, a graphical user interface is currently being implemented for the DDS. The first step of this was to decide on an appropriate framework for that GUI. After research and comparisons between different python based GUI frameworks, mock-ups was made for Textual and PyQt6. A short summary of the findings can be seen below.

| Framework | Pros                                                                       | Cons                                         |
| --------- | -------------------------------------------------------------------------- | -------------------------------------------- |
| Textual   | Low requirements, well documented, runs in the terminal, can run on alpine | Less UI flexibility                          |
| PyQt6     | Feature rich, more flexible UI                                             | Steep learning curve, does not run on alpine |

_Additional notes:_

- The fact that Textual runs in the terminal also allows the use of the GUI when using the DDS in different HPC centres.
- As mentioned in the table, Textual runs on Alpine while PyQt6 does not. Since the `dds_web` is built from an alpine image and the `dds_cli` is also installed in a container when starting up the `dds_web` (for development purposes), we either needed to choose Textual as the GUI framework or change the parent image for building the CLI.

## Decision

We will use Textual as the GUI Framework.

## Consequences

Textual runs in the terminal and has good tab completion, so users only using terminals will be able to use the GUI. Using Textual will result in UI compromises following the terminal restrictions, as well as differences in appearances depending on which terminal is used. Textual is still being actively developed with many features on the roadmap, but the current state of the framework is enough for the DDS application.
