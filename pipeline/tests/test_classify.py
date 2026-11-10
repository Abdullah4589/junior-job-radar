from jobradar.classify import clean_tags, is_software_role, looks_junior, skills_in_title


def test_software_titles_are_kept_and_other_professions_are_not():
    software = [
        "Full-Stack Developer",
        "Senior Back-end Developer",
        "Software Engineer, AI Coding Tasks",
        "UI Developer",
        "Senior Vue Developer",
        "Feltsense AI Engineer",
        "ML Inference Engineer – Terminal-Bench Task Designer",
        "DESARROLLADOR FULL STACK",
        "Security Engineer (Remote - Germany)",
        "Full-stack Engineer (f/m/d)",
        "Senior Embedded Linux Engineer (m/f/d)",
        "Cloud Engineer Automation",
        "QA Engineer",
        "Software Engineer, New Grad",
        "Autosar Cybersecurity Software Development (m/w/d)",
        "Forward Deployed Engineer - CPG/Retail",
    ]
    for title in software:
        assert is_software_role(title), title

    other = [
        "Registered Nurse",
        "Accountant",
        "Account Executive Enterprise",
        "Junior Market Analyst",
        "AI Trainer - Video Annotation",
        "Freelance Copywriter",
        "Remote Office Assistant",
        "Tier III Service Desk Engineer",
        "Revenue Cycle Manager",
        "Key Account Manager Danish Market",
        "Implementation Manager - Embedded Finance",
        "Partner Success Manager (CPM/EPM Software) EMEA",
        "Sales Manager:in / Vertrieb für Software im sozialen Bereich (m/w/d)",
        "Senior Sales Engineer - AI Agents (Western Europe, Italy)",
        "Mechanical Forward Deployed Engineer - Switzerland",
    ]
    for title in other:
        assert not is_software_role(title), title


def test_software_category_includes_head_of_engineering_only_with_category():
    assert not is_software_role("Head of Engineering")
    assert is_software_role("Head of Engineering", category="Software Development")
    assert is_software_role(
        "Internal Tools",
        tags=["Software Development"],
    )


def test_junior_detector_uses_word_boundaries():
    assert looks_junior("Junior Python Developer")
    assert looks_junior("Jr. Backend Engineer")
    assert looks_junior("Working Student Software Engineer")
    assert looks_junior("Backend Intern")
    assert looks_junior("Software Engineer", ["entry-level"])
    assert looks_junior("New Grad Data Engineer")
    assert not looks_junior("Senior Vue Developer")
    assert not looks_junior("Internal Tools Engineer")
    assert not looks_junior("Software Engineer")


def test_title_skills_do_not_split_javascript_or_trust_unrelated_remoteok_tags():
    assert skills_in_title("JavaScript Engineer") == ["javascript"]
    assert skills_in_title("Senior Java Engineer") == ["java"]
    assert skills_in_title("ASP.NET Developer") == [".net"]
    tags = clean_tags(
        ["exec", "golang", "dev", "vue", "customer support"],
        source="remoteok",
        title="Senior Vue Developer",
    )
    assert tags == ["vue"]
    assert clean_tags(
        ["exec", "engineer"],
        source="remoteok",
        title="Senior Software Engineer Case Execution",
    ) == []
    assert clean_tags(
        ["front end", "engineer"],
        source="remoteok",
        title="Front End Developer",
    ) == ["frontend"]
    assert clean_tags(
        ["Engineering (Ads)", "Python"],
        source="arbeitnow",
        title="Software Engineer",
    ) == ["python"]
