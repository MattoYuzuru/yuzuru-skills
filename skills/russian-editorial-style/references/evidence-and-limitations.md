# Evidence and limitations

This ledger supports the editing method; it is not a claim that one formula
produces universally better Russian prose. Review date: 2026-08-18.

| Design rule | Evidence | Scope and limitation |
|---|---|---|
| Start from audience ability to find, understand, and use information | [ISO 24495-1:2023](https://www.iso.org/standard/78907.html); [Fussell & Krauss, 1989](https://doi.org/10.1016/0022-1031(89)90019-X) | ISO is a standard; the experiment is English-language interpersonal communication |
| Diagnose concepts and organization, not word length alone | [Johnson & Otto, 1982](https://doi.org/10.1080/00220671.1982.10885385); [AHRQ readability guidance](https://www.ahrq.gov/talkingquality/resources/writing/tip6.html) | Mechanical simplification did not reliably improve understanding; formulas omit cohesion and task success |
| Plain language can improve comprehension, with domain-dependent effect | [Sayfi et al., 2024](https://doi.org/10.1016/j.jclinepi.2023.11.009); [Masson & Waldron, 1994](https://doi.org/10.1002/acp.2350080107) | Controlled medical and legal studies; clearer wording cannot remove conceptual difficulty |
| Prefer supported concreteness when it serves the reader | [Holmes & Langford, 1976](https://doi.org/10.1016/0022-5371(76)90050-5); [Packard & Berger, 2021](https://doi.org/10.1093/jcr/ucaa038) | Concrete language often aided memory or conveyed attention; abstraction can better signal generality in some contexts |
| Choose active/passive and nominalization by information function | [Olson & Filby, 1972](https://doi.org/10.1016/0010-0285(72)90013-8); [Millar & Budgell, 2019](https://doi.org/10.7899/JCE-17-22); [Hao & Humphrey, 2019](https://doi.org/10.1016/j.jeap.2019.100793) | Effects depend on context; nominalization also builds technical concepts |
| Use meaningful structure and explicit relations | [Lorch et al., 2013](https://doi.org/10.1016/S1135-755X(13)70011-3); [Degand et al., 1999](https://doi.org/10.1075/dd.1.1.06deg) | Headings and causal connectives improved aspects of comprehension in expository text |
| Evaluate style, content preservation, and fluency separately | [Mir et al., 2019](https://doi.org/10.18653/v1/N19-1049); [Jafaritazehjani et al., 2020](https://doi.org/10.18653/v1/2020.coling-main.197) | Text style transfer objectives conflict and style/content are not fully separable |
| Stop when the edit goal is met | [Luo et al., 2023](https://doi.org/10.18653/v1/2023.findings-emnlp.381) | Additional prompt-based edit steps improved style scores while harming content preservation |
| Run a separate content-preservation pass | [Agrawal & Carpuat, 2024](https://doi.org/10.1162/tacl_a_00653); [Pauli et al., 2025](https://doi.org/10.18653/v1/2025.findings-emnlp.1175) | Simplification systems lose answer-relevant information; automatic metrics can overstate preservation |
| Use author samples cautiously | [Wang et al., 2025](https://doi.org/10.18653/v1/2025.findings-emnlp.532); [Kadoma et al., 2024](https://doi.org/10.1145/3613904.3642650) | Subtle voice is hard to reproduce and style mismatch affects ownership |
| Do not optimize for AI detectors | [Weber-Wulff et al., 2023](https://doi.org/10.1007/s40979-023-00146-z); [Liang et al., 2023](https://doi.org/10.1016/j.patter.2023.100779); [Sadasivan et al., 2023](https://arxiv.org/abs/2303.11156) | Detectors have false positives, domain/language bias, and adversarial instability; classification is not writing quality |

## Evidence boundaries

Much causal evidence comes from English and specific professional domains.
Apply high-level principles—audience, task, structure, preservation—to Russian;
do not import language-specific thresholds. No validated universal Russian
noun/verb ratio, sentence-variance target, banned-phrase list, or “human score”
was found.

Russian detector benchmarks such as [RuATD-2022](https://arxiv.org/abs/2206.01583)
and [AINL-Eval 2025](https://arxiv.org/abs/2508.09622) classify bounded generator
and domain samples. They do not validate editorial rules for documentation,
essays, or social writing.

## Evaluation policy

Evaluate task success, audience fit, comprehension, content preservation, genre
fit, voice, grammar/naturalness, and unnecessary-edit severity separately. Use
blind pairwise human evaluation for product claims. For technical text, add
task or comprehension questions. Automatic invariant checks can find changed
artifacts; they cannot prove semantic equivalence or quality.
