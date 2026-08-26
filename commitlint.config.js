module.exports = {
    extends: ["@commitlint/config-conventional"],
    ignores: [(message) => message.includes("dependabot[bot]")],
    rules: {
        "body-max-line-length": [2, "always", 120],
        "footer-max-line-length": [2, "always", 120],
        "header-max-length": [2, "always", 72],
    },
};
