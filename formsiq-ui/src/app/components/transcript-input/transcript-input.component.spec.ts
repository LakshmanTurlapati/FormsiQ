import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TranscriptInputComponent } from './transcript-input.component';

describe('TranscriptInputComponent', () => {
  let component: TranscriptInputComponent;
  let fixture: ComponentFixture<TranscriptInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TranscriptInputComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(TranscriptInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
