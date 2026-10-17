// Politeknik Student Course Management - API Client
const API = {
  baseUrl: '',

  getToken() {
    return localStorage.getItem('politeknik_token');
  },

  setToken(token) {
    if (token) {
      localStorage.setItem('politeknik_token', token);
    } else {
      localStorage.removeItem('politeknik_token');
    }
  },

  getUser() {
    const raw = localStorage.getItem('politeknik_user');
    return raw ? JSON.parse(raw) : null;
  },

  setUser(user) {
    if (user) {
      localStorage.setItem('politeknik_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('politeknik_user');
    }
  },

  async request(endpoint, options = {}) {
    const headers = options.headers || {};
    const token = this.getToken();
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const config = {
      ...options,
      headers
    };

    try {
      const response = await fetch(endpoint, config);
      
      // Auto handle 401 Unauthorized
      if (response.status === 401 && !endpoint.includes('/api/auth/login')) {
        this.setToken(null);
        this.setUser(null);
        window.dispatchEvent(new CustomEvent('auth:expired'));
        throw new Error('Session expired. Please log in again.');
      }

      if (response.headers.get('content-type')?.includes('application/json')) {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || data.message || 'Request failed');
        }
        return data;
      }

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Request failed');
      }

      return response;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  // Auth
  async login(username, password) {
    const res = await this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    this.setToken(res.token);
    this.setUser(res.user);
    return res;
  },

  async register(data) {
    return await this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async me() {
    return await this.request('/api/auth/me');
  },

  async logout() {
    try {
      await this.request('/api/auth/logout', { method: 'POST' });
    } finally {
      this.setToken(null);
      this.setUser(null);
    }
  },

  async changePassword(user_identifier, new_password) {
    return await this.request('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ user_identifier, new_password })
    });
  },

  async getAdvisors() {
    return await this.request('/api/advisors');
  },

  // Students
  async getStudents(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.program) query.append('program', params.program);
    if (params.advisor_id) query.append('advisor_id', params.advisor_id);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return await this.request(`/api/students${qs}`);
  },

  async getStudentDetails(matric) {
    return await this.request(`/api/students/${encodeURIComponent(matric)}/details`);
  },

  async addStudent(studentData) {
    return await this.request('/api/students', {
      method: 'POST',
      body: JSON.stringify(studentData)
    });
  },

  async updateStudent(matric, studentData) {
    return await this.request(`/api/students/${encodeURIComponent(matric)}`, {
      method: 'PUT',
      body: JSON.stringify(studentData)
    });
  },

  async deleteStudent(matric) {
    return await this.request(`/api/students/${encodeURIComponent(matric)}`, {
      method: 'DELETE'
    });
  },

  async syncMetrics() {
    return await this.request('/api/students/sync-metrics', { method: 'POST' });
  },

  // Courses
  async getCourses(params = {}) {
    const query = new URLSearchParams();
    if (params.cohort) query.append('cohort', params.cohort);
    if (params.program) query.append('program', params.program);
    if (params.semester) query.append('semester', params.semester);
    if (params.search) query.append('search', params.search);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return await this.request(`/api/courses${qs}`);
  },

  async addCourse(courseData) {
    return await this.request('/api/courses', {
      method: 'POST',
      body: JSON.stringify(courseData)
    });
  },

  async updateCourse(code, courseData) {
    return await this.request(`/api/courses/${encodeURIComponent(code)}`, {
      method: 'PUT',
      body: JSON.stringify(courseData)
    });
  },

  async deleteCourse(code) {
    return await this.request(`/api/courses/${encodeURIComponent(code)}`, {
      method: 'DELETE'
    });
  },

  async getCohorts() {
    return await this.request('/api/courses/cohorts');
  },

  async getPrograms() {
    return await this.request('/api/courses/programs');
  },

  // Prerequisites
  async addPrerequisite(course_code, prereq_code) {
    return await this.request('/api/prerequisites', {
      method: 'POST',
      body: JSON.stringify({ course_code, prereq_code })
    });
  },

  async deletePrerequisite(course_code, prereq_code) {
    return await this.request(`/api/prerequisites?course_code=${encodeURIComponent(course_code)}&prereq_code=${encodeURIComponent(prereq_code)}`, {
      method: 'DELETE'
    });
  },

  // Enrollments
  async getEnrollments(params = {}) {
    const query = new URLSearchParams();
    if (params.student_id) query.append('student_id', params.student_id);
    if (params.semester) query.append('semester', params.semester);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return await this.request(`/api/enrollments${qs}`);
  },

  async addEnrollment(data) {
    return await this.request('/api/enrollments', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async updateEnrollment(id, data) {
    return await this.request(`/api/enrollments/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  },

  async deleteEnrollment(id) {
    return await this.request(`/api/enrollments/${id}`, {
      method: 'DELETE'
    });
  },

  // Planner
  async getPlanner(student_id) {
    return await this.request(`/api/planner/${encodeURIComponent(student_id)}`);
  },

  // Import
  async importFile(file, import_type = 'All', sheet_name = null) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('import_type', import_type);
    if (sheet_name) formData.append('sheet_name', sheet_name);

    return await this.request('/api/import', {
      method: 'POST',
      body: formData
    });
  }
};
