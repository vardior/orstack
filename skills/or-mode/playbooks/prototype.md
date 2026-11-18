### Prototype

**You own the design decision, not the code. The prototype is a throwaway instrument; the real build follows Feature.** For "prototype", "mock it up", "sketch this", "try this layout" — and for settling an empirical fork (which behavior, which timing, which approach) by observing it run, when you would otherwise ask the human a question a quick sketch could answer.

The one playbook where "smallest change" and the verification bar invert. Speed over polish; code quality does not matter; no planning. The rigor is in picking the right design cheaply. Be bold: propose variations the user didn't ask for, throw an approach away and try another.

1. Scope the decision the prototype exists to make. No decision means no prototype; route to Feature.
2. Gather references when the design space is open (prior art, a moodboard of directions). Skip when the direction is set.
3. Build throwaway in an isolated scratch dir, separate from production source. Visual decision: vanilla HTML/CSS/JS or the lightest stack that renders the idea. Behavioral or timing decision: the smallest script that exercises the question. No production framework, no tests, no abstractions.
4. When comparing alternatives, build them behind one switcher (buttons or a keypress), each variant labeled so the user can name it.
5. Verify on the matching surface. Visual: screenshot each variant with the active runtime's browser and drive the interaction; the eye is the test. Behavioral: log the timing, print the output, watch it run. The observation is the test, not an assertion.
6. Present alternatives, tradeoffs, and a recommendation. The output is the decision plus the throwaway artifact, not shippable code. Hand the chosen direction to **Feature** (or `design-it-twice` for the shape) for the real build.

**Reply:** the variants explored, the evidence (screenshots or observed output), tradeoffs, your recommendation, and the scratch path. Say plainly that the prototype is throwaway.
