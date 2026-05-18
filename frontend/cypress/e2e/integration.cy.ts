describe('DeepStegAI Integration Flow', () => {
  it('Should successfully login, upload an image, embed data, and download result', () => {
    // 1. Visit Login Page
    cy.visit('/login');
    cy.get('input[type="email"]').type('integration_test@example.com');
    cy.get('input[type="password"]').type('StrongPassword123');
    cy.get('button[type="submit"]').click();
    
    // Check if redirect successful
    cy.url().should('include', '/dashboard');
    cy.get('.toast').should('contain', 'Login successful');

    // 2. Navigate to Single Image Processing
    cy.get('a[href="/embed"]').click();

    // 3. File Uploads (Attach Cover and Payload)
    cy.fixture('test_cover.png', null).as('coverFile');
    cy.get('input[type="file"][name="cover"]').selectFile('@coverFile', { force: true });
    
    cy.fixture('secret.txt', null).as('textFile');
    cy.get('input[type="file"][name="secret"]').selectFile('@textFile', { force: true });

    // 4. Fill Options and Submit
    cy.get('input[name="password"]').type('StegoPassword123');
    cy.get('button[type="submit"]').click();

    // 5. Assert API Chaining / Loading State
    cy.get('.spinner').should('be.visible');
    
    // 6. Verify Result and Data Consistency
    cy.get('.result-preview').should('be.visible');
    cy.get('.toast').should('contain', 'Embedded successfully');
    cy.get('p').should('contain', 'Credits remaining'); // Checks DB sync
    
    // Verify Download Link is active
    cy.get('a.download-btn').should('have.attr', 'href').and('include', 'data:image/png;base64');
  });
});
