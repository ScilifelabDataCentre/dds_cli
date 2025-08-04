# 1. Use Textual as GUI Framework

Date: Spring 2025

## Status

Accepted

## Context

In order to allow users to take advantage of the DDS functionality without requiring the use of a terminal / command line, a graphical user interface is currently being implemented for the DDS. The first step of this was to decide on an appropriate framework for that GUI. After research and comparisons between different python based GUI frameworks, mock-ups was made for Textual and PyQt6. A short summary of the findings can be seen below.

| Framework | Pros                                                                      | Cons                                         |
| --------- | ------------------------------------------------------------------------- | -------------------------------------------- |
| Textual   | Low requirments, well documented, runs in the terminal, can run on alpine | Less UI flexibility                          |
| PyQt6     | Feature rich, more flexible UI                                            | Steep learning curve, does not run on alpine |

## Decision

We will use Textual as the GUI Framework.

## Consequences

Textual runs in the termainal and has good tab completion, so users only using terminals will be able to use the GUI. Using Textual will result in UI compromises following the terminal restrictions, as well as differences in appearances depending on which terminal is used. Textual is still beeing activly developed with many features on the roadmap, but the current state of the framework is enough for the DDS application.
