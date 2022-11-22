
format:
	black tutorkdmccormick

test-static: test-format test-lint test-types

test-format:
	black --check tutorkdmccormick

test-lint:
	pylint tutorkdmccormick

test-types: 
	mypy tutorkdmccormick
