# Contributing to Fantasy Draft Engine

Thank you for your interest in contributing to the Fantasy Draft Engine! This project aims to democratize data-driven fantasy football draft strategies through machine learning.

## Table of Contents
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Git
- 4GB+ RAM (for ML model training)
- Basic understanding of fantasy football and machine learning concepts

### Areas for Contribution

We welcome contributions in these areas:

#### 🤖 **Machine Learning & Data Science**
- Feature engineering improvements
- New model architectures (neural networks, ensemble methods)
- Model interpretability and explainability features
- Hyperparameter optimization
- Cross-validation strategies

#### 📊 **Data Integration**
- Real-time injury report integration
- Weather impact modeling
- Vegas odds integration
- Beat reporter sentiment analysis
- Historical trade data

#### 🏈 **Fantasy Football Domain**
- Position-specific insights and features
- Scoring system variations (auction, dynasty, keeper leagues)
- Draft strategy optimization
- Trade value analysis
- Waiver wire projections

#### 🛠 **Software Engineering**
- API development and optimization
- Frontend/UI development
- Database optimization
- Testing infrastructure
- CI/CD improvements

#### 📖 **Documentation & Education**
- Tutorial creation
- Code documentation
- Fantasy football education content
- Model explanation guides

## Development Setup

### 1. Fork and Clone
```bash
# Fork the repository on GitHub, then:
git clone https://github.com/yourusername/fantasy_draft_engine.git
cd fantasy_draft_engine
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Tests
```bash
pytest tests/
```

### 5. Generate Sample Rankings
```bash
python scripts/main.py
```

## Contributing Guidelines

### Issue Reports
- Use clear, descriptive titles
- Provide steps to reproduce bugs
- Include system information (OS, Python version)
- Attach relevant error messages and logs

### Feature Requests
- Explain the fantasy football use case
- Describe expected behavior
- Consider implementation complexity
- Discuss potential impact on existing features

### Pull Requests
- Reference related issues
- Include tests for new functionality
- Update documentation as needed
- Follow the code style guidelines

## Code Standards

### Python Style
- Follow PEP 8 with these exceptions:
  - Line length: 100 characters (not 79)
  - Use double quotes for strings
- Use type hints for all function parameters and returns
- Include docstrings for all public functions

### Example Function
```python
def calculate_vor_score(player_points: float, replacement_points: float, 
                       position: str) -> float:
    """
    Calculate Value Over Replacement for a fantasy player.
    
    Args:
        player_points: Projected fantasy points for the player
        replacement_points: Replacement level points for the position
        position: Player position (QB, RB, WR, TE, K, DST)
    
    Returns:
        VOR score (positive means above replacement level)
        
    Example:
        >>> calculate_vor_score(300, 250, "RB")
        50.0
    """
    return player_points - replacement_points
```

### Data Science Standards
- Use pandas for data manipulation
- Use scikit-learn for standard ML algorithms
- Include model validation and cross-validation
- Document feature engineering rationale
- Provide model interpretation when possible

### File Organization
```
src/
├── data/           # Data loading and processing
├── models/         # ML model implementations  
├── ranking/        # Draft ranking logic
└── utils/          # Utility functions

scripts/            # Entry point scripts
tests/             # Test files
docs/              # Documentation
```

## Testing

### Running Tests
```bash
# All tests
pytest

# Specific test categories
pytest tests/test_models.py -v
pytest tests/test_ranking.py -v
pytest tests/test_data.py -v

# With coverage
pytest --cov=src --cov-report=html
```

### Writing Tests
- Use pytest for all tests
- Mock external API calls
- Test edge cases (empty data, invalid inputs)
- Include integration tests for full pipeline

### Test Example
```python
def test_vor_calculation():
    """Test VOR calculation with known values."""
    vor_calc = VORCalculator()
    test_data = pd.DataFrame({
        'player_name': ['Player A', 'Player B', 'Player C'],
        'position': ['RB', 'RB', 'RB'],
        'predicted_points': [300, 250, 200]
    })
    
    result = vor_calc.calculate_vor_scores(test_data)
    
    # Player A should have highest VOR
    assert result.iloc[0]['vor'] > result.iloc[1]['vor']
    assert result.iloc[1]['vor'] > result.iloc[2]['vor']
```

## Documentation

### Code Documentation
- Use Google-style docstrings
- Include parameter types and descriptions
- Provide usage examples
- Document any fantasy football domain knowledge

### README Updates
- Keep installation instructions current
- Update feature lists when adding functionality
- Include performance benchmarks
- Add screenshots for UI changes

### CLAUDE.md Updates
- Add new essential commands
- Update domain knowledge section
- Document new best practices
- Include configuration changes

## Submitting Changes

### Commit Guidelines
```bash
# Use descriptive commit messages
git commit -m "feat: add injury impact modeling for RB projections"
git commit -m "fix: resolve VOR calculation edge case for kickers"
git commit -m "docs: update installation guide for Python 3.11"
```

### Commit Types
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation updates
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `perf:` Performance improvements

### Pull Request Process
1. **Create Branch**: Use descriptive branch names
   ```bash
   git checkout -b feature/injury-impact-modeling
   git checkout -b fix/vor-calculation-bug
   ```

2. **Make Changes**: Follow code standards and include tests

3. **Update Documentation**: Update relevant docs and CLAUDE.md

4. **Submit PR**: 
   - Use clear title and description
   - Reference related issues
   - Include testing information
   - Request review from maintainers

5. **Address Feedback**: Respond to review comments promptly

## Fantasy Football Considerations

### Domain Knowledge Required
Contributors should understand:
- Basic fantasy football scoring (PPR, Standard)
- Position scarcity and value (VOR concept)
- Draft strategies (Zero RB, Robust RB, etc.)
- Season-long vs weekly projections
- Injury impact on player value

### Data Considerations
- **Seasonality**: NFL seasons are short (17 games)
- **Sample Size**: Limited data for rookies and injured players
- **Position Differences**: Each position has unique predictive features
- **Scoring Variations**: Different league scoring systems
- **Real-time Updates**: Injury news changes player values quickly

### Model Considerations
- **Interpretability**: Fantasy users want to understand rankings
- **Uncertainty**: Confidence intervals are important
- **Position Balance**: Avoid over-optimizing for one position
- **User Trust**: Rankings should pass "common sense" tests

## Getting Help

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: General questions and brainstorming
- **Pull Request Reviews**: Code-specific feedback

### Resources
- [Fantasy Football Analytics](https://www.fantasyfootballanalytics.net/)
- [nflverse Documentation](https://nflverse.nflverse.com/)
- [Scikit-learn User Guide](https://scikit-learn.org/stable/user_guide.html)
- [Fantasy Football Subreddit](https://www.reddit.com/r/fantasyfootball/)

### Mentorship
New contributors are welcome! Maintainers are happy to:
- Help with development environment setup
- Provide fantasy football domain guidance
- Review code and suggest improvements
- Pair program on complex features

## Code of Conduct

### Our Standards
- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment
- Remember we're all learning

### Fantasy Football Etiquette
- Respect different draft strategies and opinions
- Share knowledge and insights freely
- Focus on data-driven discussions
- Avoid promoting gambling or unethical practices

## Recognition

Contributors will be recognized in:
- README.md contributor section
- Release notes for significant contributions
- Special thanks for first-time contributors
- Maintainer status for sustained contributions

---

Thank you for contributing to Fantasy Draft Engine! Together we can build the best open-source fantasy football tool. 🏈📊