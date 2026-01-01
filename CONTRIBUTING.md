# Contributing to NatLangChain

Thank you for your interest in contributing to NatLangChain! This document provides guidelines and information for contributors.

## Getting Started

1. **Read the documentation**: Familiarize yourself with the [Technical Specification](SPEC.md) and the [NCIP Governance Framework](docs/NCIP-000+.md).
2. **Understand the architecture**: NatLangChain is part of a 12-repository ecosystem. See the SPEC.md for the full repository map.
3. **Set up your environment**: Follow the [Installation Guide](INSTALLATION.md).

## How to Contribute

### Reporting Issues

- Use GitHub Issues to report bugs or suggest features
- Search existing issues before creating a new one
- Provide clear reproduction steps for bugs
- Include relevant logs and environment information

### Code Contributions

1. **Fork the repository** and create a feature branch
2. **Follow existing code style** and patterns
3. **Write tests** for new functionality
4. **Update documentation** as needed
5. **Submit a Pull Request** with a clear description

### Documentation Contributions

- Improvements to existing docs are welcome
- New documentation should align with the NCIP governance framework
- Use clear, precise language (per NCIP-000 terminology governance)

## NCIP Process

For significant changes to protocol semantics or governance:

1. **Read NCIP-000** (Terminology & Semantics Governance)
2. **Check NCIP-014** (Protocol Amendments & Constitutional Change)
3. **Draft an NCIP** following the established format
4. **Submit for review** via Pull Request

### NCIP Guidelines

- NCIPs cannot redefine semantics established by lower-numbered NCIPs
- New terms must avoid collision with existing canonical terms
- Changes require explicit backward-compatibility analysis

## Code Standards

### Python

- Follow PEP 8 style guidelines
- Use type hints where practical
- Write docstrings for public functions
- Keep functions focused and testable

### Documentation

- Use Markdown format
- Follow existing document structure
- Reference NCIPs and SPEC.md where applicable
- Keep language precise and unambiguous

## Pull Request Process

1. **Ensure all tests pass** before submitting
2. **Update SPEC.md** if your change affects the specification
3. **Reference related issues** in your PR description
4. **Request review** from maintainers
5. **Address feedback** promptly

### PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] SPEC.md updated (if applicable)
- [ ] No breaking changes (or clearly documented)
- [ ] Follows NCIP governance (for semantic changes)

## Governance

NatLangChain uses a layered governance model:

- **NCIP Framework**: Semantic and protocol governance (see docs/NCIP-000+.md)
- **MP Suite**: Mediator Protocol specifications (MP-01 through MP-05)
- **Technical Specification**: Implementation details (SPEC.md)

## Community

- Be respectful and constructive
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)
- Help others learn and contribute

## License

By contributing, you agree that your contributions will be licensed under the project's CC BY-SA 4.0 license.

---

**Questions?** Open an issue or consult the [FAQ](FAQ.md).

**Last Updated:** January 1, 2026
