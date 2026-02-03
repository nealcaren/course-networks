// Registration form handling

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('registration-form');
    const studentIdInput = document.getElementById('student-id');
    const studentIdError = document.getElementById('student-id-error');
    const coursesContainer = document.getElementById('courses-container');
    const addCourseBtn = document.getElementById('add-course');
    const submitBtn = document.getElementById('submit-btn');
    const formMessage = document.getElementById('form-message');

    // Student ID validation
    function validateStudentId(value) {
        const pattern = /^[A-Za-z]\d{4}$/;
        return pattern.test(value.trim());
    }

    // Course validation
    function validateCourse(value) {
        const cleaned = value.trim().toUpperCase().split('.')[0].replace(/\s+/g, '');
        const pattern = /^[A-Z]{4}\d{2,3}$/;
        return pattern.test(cleaned);
    }

    // Real-time student ID validation
    studentIdInput.addEventListener('input', function() {
        const value = this.value.trim();
        if (value && !validateStudentId(value)) {
            studentIdError.textContent = 'Format: 1 letter + 4 digits (e.g., C1234)';
            this.classList.add('invalid');
        } else {
            studentIdError.textContent = '';
            this.classList.remove('invalid');
        }
    });

    // Add course entry
    function addCourseEntry() {
        const entry = document.createElement('div');
        entry.className = 'course-entry';
        entry.innerHTML = `
            <input type="text" class="course-input" placeholder="e.g., PSYC 210" required>
            <button type="button" class="btn-remove">Remove</button>
        `;
        coursesContainer.appendChild(entry);
        updateRemoveButtons();

        // Add validation listener
        const input = entry.querySelector('.course-input');
        input.addEventListener('input', handleCourseInput);
        input.focus();
    }

    // Handle course input validation
    function handleCourseInput(e) {
        const value = e.target.value.trim();
        if (value && !validateCourse(value)) {
            e.target.classList.add('invalid');
        } else {
            e.target.classList.remove('invalid');
        }
    }

    // Remove course entry
    function removeCourseEntry(entry) {
        entry.remove();
        updateRemoveButtons();
    }

    // Update remove button states
    function updateRemoveButtons() {
        const entries = coursesContainer.querySelectorAll('.course-entry');
        entries.forEach((entry, index) => {
            const btn = entry.querySelector('.btn-remove');
            btn.disabled = entries.length === 1;
        });
    }

    // Add course button click
    addCourseBtn.addEventListener('click', addCourseEntry);

    // Remove button click (event delegation)
    coursesContainer.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-remove')) {
            const entry = e.target.closest('.course-entry');
            removeCourseEntry(entry);
        }
    });

    // Course input validation (event delegation)
    coursesContainer.addEventListener('input', function(e) {
        if (e.target.classList.contains('course-input')) {
            handleCourseInput(e);
        }
    });

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Validate student ID
        const studentId = studentIdInput.value.trim();
        if (!validateStudentId(studentId)) {
            showMessage('Invalid student ID format', 'error');
            studentIdInput.focus();
            return;
        }

        // Gather and validate courses
        const courseInputs = coursesContainer.querySelectorAll('.course-input');
        const courses = [];

        for (const input of courseInputs) {
            const value = input.value.trim();
            if (!value) {
                showMessage('Please fill in all course fields', 'error');
                input.focus();
                return;
            }
            if (!validateCourse(value)) {
                showMessage(`Invalid course format: "${value}"`, 'error');
                input.focus();
                return;
            }
            courses.push(value);
        }

        // Submit registration
        submitBtn.disabled = true;
        submitBtn.textContent = 'Registering...';

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    student_id: studentId,
                    courses: courses
                })
            });

            const data = await response.json();

            if (response.ok) {
                showMessage(`Successfully registered ${data.student_id} with ${data.courses.length} courses!`, 'success');
                // Reset form
                form.reset();
                // Reset course entries to single
                coursesContainer.innerHTML = `
                    <div class="course-entry">
                        <input type="text" class="course-input" placeholder="e.g., SOCI 101" required>
                        <button type="button" class="btn-remove" disabled>Remove</button>
                    </div>
                `;
            } else {
                showMessage(data.error || 'Registration failed', 'error');
            }
        } catch (error) {
            showMessage('Network error. Please try again.', 'error');
            console.error('Registration error:', error);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Register';
        }
    });

    // Show message helper
    function showMessage(text, type) {
        formMessage.textContent = text;
        formMessage.className = `form-message ${type}`;

        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                formMessage.textContent = '';
                formMessage.className = 'form-message';
            }, 5000);
        }
    }
});
