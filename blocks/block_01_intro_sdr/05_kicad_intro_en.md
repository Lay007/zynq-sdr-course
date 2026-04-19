# 05. Introduction to KiCad

## Purpose of the section
To become familiar with the role of KiCad in the course and understand how the circuit-design part is related to SDR experiments.

## 1. Why KiCad is needed in an SDR course
At first glance, an SDR course might seem limited to:
- DSP;
- modeling;
- FPGA;
- software processing.

However, a real engineering experiment almost always includes a hardware side:
- power;
- interconnects;
- matching;
- generators;
- support circuits;
- adapters and boards.

That is why **KiCad** is introduced into the course as a tool for:
- reading electrical schematics;
- drawing your own schematics;
- preparing simple PCBs;
- creating a bill of materials and documentation.

## 2. Role of KiCad in the first block
In the first block KiCad is used in a **lightweight format**.

The student’s task is to:
- get familiar with the interface;
- open a ready-made schematic;
- learn to read component symbols;
- understand how the schematic is related to the real setup.

At this stage deep PCB routing is not required.

## 3. What the student should see in KiCad
At the level of the first block it is useful to show:
- a power source;
- connectors;
- signal lines;
- ground;
- component symbols;
- simple generation or matching chains;
- relationships between schematic blocks.

This helps move from a “black box” view to engineering understanding.

## 4. Why this matters already at the beginning
Even if the first laboratory work is focused on receiving a test signal, the student should understand:
- where the signal comes from;
- how it is connected electrically;
- which subsystems participate in the experiment;
- what happens between the board, the breadboard, and the cables.

Without that, the course risks turning into a set of software exercises without real hardware thinking.

## 5. What KiCad will be used for later
In later stages of the course, KiCad can be used for:
- schematics of a tone-pulse generator built from analog components;
- schematics of a generator built from basic digital logic ICs;
- simple power and interconnection boards;
- adapters for experimental chains;
- documentation of educational circuits.

Thus KiCad becomes a link between:
- theory;
- experiment;
- documentation;
- hardware engineering culture.

## 6. What is useful to show in the KiCad interface
For the first introduction it is enough to explain:
- the project window;
- the schematic editor;
- library components;
- connections between elements;
- net labels;
- annotation;
- ERC as a basic schematic check;
- PCB and 3D view only at a high level.

## 7. How to read a simple schematic
When reading a schematic, the student should be able to answer:

1. Where is the power source?
2. Where is ground?
3. Which elements form the signal?
4. Where does the signal go next?
5. Which connectors are used?
6. Which nets are service nets and which are signal nets?

If the student can answer these questions, then the schematic is no longer just a set of symbols.

## 8. Relationship between schematic and breadboard
One important purpose of KiCad in the course is to help the student move from a schematic to a physical assembly.

That is:
- the schematic shows the electrical logic;
- the breadboard shows the physical implementation;
- the SDR experiment shows the practical result.

The triad
**schematic → assembly → measurement**
is an important part of engineering culture.

## 9. Relationship between schematic and SDR experiment
For this course it is especially important to understand that circuit design does not exist separately from SDR.

For example:
- a generator schematic may form a test pulse;
- an interface schematic may connect to the SDR board;
- power and switching circuits influence experiment quality;
- poor layout or incorrect wiring can ruin the result of DSP processing.

Therefore KiCad is not a “side” tool but part of the overall course logic.

## 10. Practical task of the first introduction
In the first block the student can be given a simple task:

- open a ready-made KiCad project;
- find the power source;
- find the signal output;
- determine which elements belong to signal generation;
- find the connector used to connect the node to the setup;
- briefly describe the purpose of the schematic.

## 11. Conclusions
After studying this section, the student should understand:
- why KiCad is included in the SDR course;
- how to read a simple schematic;
- how the schematic is connected to the real experiment;
- what role the circuit-design part will play later.

## Review questions
1. Why is KiCad needed in this course?
2. Why is it important to learn schematic reading early?
3. Which basic elements must be found on a schematic?
4. How are the schematic, the breadboard assembly, and the SDR experiment connected?
5. Which tasks will KiCad solve in later blocks?
