import config from "semantic-release-preconfigured-conventional-commits" with {
  type: "json",
};

// Set by deploy.yml: dry run off master/main and on the initial commit.
const dryRun = (process.env.RELEASE_DRY_RUN || "false").toLowerCase() === "true";

// Poetry reads the PyPI token from POETRY_PYPI_TOKEN_PYPI. deploy.yml provides the
// secret as PYPI_TOKEN; copy it here so the token never appears in a command line.
if (process.env.PYPI_TOKEN && !process.env.POETRY_PYPI_TOKEN_PYPI) {
  process.env.POETRY_PYPI_TOKEN_PYPI = process.env.PYPI_TOKEN;
}

// Build and publish the Python package.
config.plugins.push(
  [
    "@semantic-release/exec",
    {
      prepareCmd: "poetry version ${nextRelease.version}",
      publishCmd: "poetry publish --build",
    },
  ],
  [
    "@semantic-release/github",
    {
      assets: [{ path: "dist/*" }],
    },
  ],
  [
    "@semantic-release/git",
    {
      assets: ["CHANGELOG.md", "pyproject.toml"],
      message: "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}",
    },
  ],
);

config.dryRun = dryRun;

export default config;
