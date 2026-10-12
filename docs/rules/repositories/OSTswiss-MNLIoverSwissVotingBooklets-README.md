Source URL: https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets/raw/main/README.md
Fetch date: 2026-10-12

---
license: mit
task_categories:
- text-classification
language:
- fr
- de
- it
tags:
- entailment
- politics
- switzerland
- voting
- multilingual
pretty_name: MNLI over Swiss Voting Booklets
size_categories:
- 1K<n<10K
---
# MNLI over Swiss Voting Booklets: Benchmark Dataset  

## Dataset Contents  

### Fields  

|        **Field Name**   | **Data Type** | **Possible Content** | **Description**                                                                                                                                                                                                                                                                                  |
|-------------------------|---------------|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `claim`                 | `string`      | Raw Text             | Claim about the contents of a voting booklet. May be entailed, contradictory or unrelated to its source material.                                                                                                                                                                                |
| `claim_language`        | `string`      | [`de`, `fr`, `it`]   | The language the claim is written in. May be German (`de`), French (`fr`) or Italian (`it`). Does not need to match the `reference_language`.                                                                                                                                                    |
| `reference_string`      | `string`      | Raw Text             | A text snippet from the voting booklet that was used to generate the `claim`.                                                                                                                                                                                                                    |
| `entailment_label`      | `int`         | [`0`, `1`, `2`]      | The entailment class of the `claim` relative to the `reference_string` and voting booklet as a whole. May be `Entailment` (`0`), `Unrelated / Neutral` (`1`) or `Contradiction` (`2`).                                                                                                           |
| `baseline_score`        | `float`       | [`0.0`,...,`1.0`]    | The certainty about the label correctness of the classifier used for validation.                                                                                                                                                                                                                 |
| `reference_language`    | `string`      | [`de`, `fr`, `it`]   | The language the `reference_string` and corresponding voting booklet is written in. May be German (`de`), French (`fr`) or Italian (`it`). Does not need to match the `claim_language`.                                                                                                          |
| `booklet_publish_date`  | `string`      | `YYYY-MM-DD`         | The date at which the voting booklet was published.                                                                                                                                                                                                                                              |
| `booklet_download_date` | `string`      | `YYYY-MM-DD`         | The date at which the booklet was downloaded for the creation of the dataset.                                                                                                                                                                                                                    |
| `booklet_url`           | `string`      | `URL`                | Download link for the full booklet as a PDF.                                                                                                                                                                                                                                                     |
| `vote`                  | `string`      | Raw Text             | Name of the vote the `claim` is about. Can be used to verify ambiguous claims about a booklet containing multiple votes, e.g. `Der Bundesrat empfiehlt, die Initiative abzulehnen.` (`The federal council recommends to reject the initiative.`) when the booklet contains multiple initiatives. |

### Sampling Ratios  

To create the dataset, we sampled a larger corpus of `claim` / `reference_string` pairs for rows fulfilling specific criteria to ensure that the resulting dataset is balanced.  
We specifically designed the dataset to target...

- ... a uniform distribution over the `claim_language` field.  
- ... a uniform distribution over the `entailment_label` field.  
- ... an approximately `0.5 / 0.35 / 0.15` split of `easy / medium / hard` claims to classify, based on the `baseline_score` provided by our validation model.  

## How to Use the Dataset (Quick Start in Python)  

Install the `datasets` package with a package manager of your choice. E.g. `uv` on Linux:

```console
> mkdir my-project
> cd my-project/
> uv init
> uv add datasets
```

You can then download and use this dataset with the `load_dataset` function as such:

```python
from datasets import load_dataset

dataset = load_dataset("OSTswiss/MNLIoverSwissVotingBooklets")
print(dataset)
```

For more information or alternative approaches, consult the [Downloading datasets](https://huggingface.co/docs/hub/en/datasets-downloading) page by Hugging Face.

## Additional Information  

### Hack Apertus  

This dataset was created as part of the `Hack Apertus` hackathon series. If you want to participate or contribute, you can find more information on [https://hackapertus.ch/](https://hackapertus.ch/).  

### Credit  

This Dataset was created by the `AI Applications and Deployment Lab`, part of the `Institute for Software (IFS)` at `Eastern Switzerland University of Applied Sciences OST` ([Website](https://www.ost.ch/en/research-and-consulting-services/computer-science/ifs-institute-for-software/ai-applications-and-deployment-lab)).  

Special thanks go out to the Development Team:  

- Prof. Dr. Mitra Purandare, `mitra.purandare@ost.ch`, [ Project Lead, Hackathon Task Design ]  
- Abinas Kuganathan, `abinas.kuganathan@ost.ch`, [ Hackathon Task Design, Programming ]  
- Dominik Castelberg, `dominik.castelberg@ost.ch`, [ Dataset Design, Programming ]  
- Vladimir Zivanovic, `vladimir.zivanovic@ost.ch`, [ Programming ]