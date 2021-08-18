import logging
from pathlib import Path
from typing import Dict, Optional

import yaml
from github import Github
from pydantic import BaseModel, BaseSettings, SecretStr

awaiting_label = "awaiting review"
lang_all_label = "lang-all"
approved_label = "approved-2"
translations_path = Path(__file__).parent / "translations.yml"


class Settings(BaseSettings):
    github_repository: str
    input_token: SecretStr
    github_event_path: Path
    github_event_name: Optional[str] = None
    input_debug: Optional[bool] = False


class PartialGitHubEventIssue(BaseModel):
    number: int


class PartialGitHubEvent(BaseModel):
    pull_request: PartialGitHubEventIssue


if __name__ == "__main__":
    settings = Settings()
    if settings.input_debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logging.debug(f"Using config: {settings.json()}")
    g = Github(settings.input_token.get_secret_value())
    repo = g.get_repo(settings.github_repository)
    if not settings.github_event_path.is_file():
        raise RuntimeError(
            f"No github event file available at: {settings.github_event_path}"
        )
    contents = settings.github_event_path.read_text()
    github_event = PartialGitHubEvent.parse_raw(contents)
    translations_map: Dict[str, int] = yaml.safe_load(translations_path.read_text())
    logging.debug(f"Using translations map: {translations_map}")
    pr = repo.get_pull(github_event.pull_request.number)
    logging.debug(f"Processing PR: {pr.number}")
    if pr.state == "open":
        logging.debug(f"PR is open: {pr.number}")
        label_strs = set([label.name for label in pr.get_labels()])
        if lang_all_label in label_strs and awaiting_label in label_strs:
            logging.info(
                f"This PR seems to be a language translation and awaiting reviews: {pr.number}"
            )
            if approved_label in label_strs:
                message = (
                    f"It seems this PR already has the approved label: {pr.number}"
                )
                logging.error(message)
                raise RuntimeError(message)
            langs = []
            for label in label_strs:
                if label.startswith("lang-") and not label == lang_all_label:
                    langs.append(label[5:])
            for lang in langs:
                if lang in translations_map:
                    num = translations_map[lang]
                    logging.info(f"Found a translation issue for {lang}: {num}")
                    issue = repo.get_issue(num)
                    issue.create_comment(
                        f"Good news everyone! 😉 There's a new translation PR to be reviewed: #{pr.number} 🎉"
                    )
    else:
        logging.info(
            f"Changing labels in a closed PR doesn't trigger comments, PR: {pr.number}"
        )
    logging.info("Finished")
