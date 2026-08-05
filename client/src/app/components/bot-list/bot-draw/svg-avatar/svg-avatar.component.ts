import { Component, ViewChild, Input, OnInit, AfterViewInit, ElementRef, Renderer2, OnDestroy, ChangeDetectorRef, OnChanges, SimpleChanges } from '@angular/core';
import { SvgBotComponent } from '../svg-bot/svg-bot.component';
import { SvgHatComponent } from '../svg-hat/svg-hat.component';
import { SvgMouthComponent } from '../svg-mouth/svg-mouth.component';
import { SvgEyesComponent } from '../svg-eyes/svg-eyes.component';
import { CommonModule } from '@angular/common';
import { v4 as uuidv4 } from 'uuid';
import { Avatar } from '@app/models/avatar.model';

@Component({
  selector: 'app-svg-avatar',
  standalone: true,
  imports: [
    SvgBotComponent,
    SvgHatComponent,
    SvgMouthComponent,
    SvgEyesComponent,
    CommonModule
  ],
  templateUrl: './svg-avatar.component.html',
  styleUrl: './svg-avatar.component.scss'
})
export class SvgAvatarComponent implements OnInit, AfterViewInit, OnDestroy, OnChanges {
  static id: string = uuidv4();

  @Input() avatar!: Avatar;

  @ViewChild('svgContainer', { static: false }) svgContainerRef!: ElementRef;

  actualWidthInPx: number = 0;
  private resizeObserver?: ResizeObserver;
  private intersectionObserver?: IntersectionObserver;

  constructor(
    private renderer: Renderer2,
    private el: ElementRef,
    private cdr: ChangeDetectorRef
  ) {}
  ngOnChanges(changes: SimpleChanges): void {
    // this.getActualWidth();

    // // Observer les changements de visibilité
    // this.setupIntersectionObserver();

    // // Observer les changements de taille
    // this.setupResizeObserver();
    // console.log('SVG Avatar component changes detected:', changes);
  }

  ngOnInit(): void {
    this.refresh();
  }

  ngAfterViewInit(): void {
    // Récupérer la largeur réelle après le rendu du composant
    this.getActualWidth();

    // Observer les changements de visibilité
    this.setupIntersectionObserver();

    // Observer les changements de taille
    this.setupResizeObserver();
    console.log('SVG Avatar initialized :', this.actualWidthInPx);
  }

  ngOnDestroy(): void {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
    }
  }

  private setupIntersectionObserver(): void {
    this.intersectionObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          // L'élément est devenu visible, recalculer les dimensions
          setTimeout(() => {
            this.getActualWidth();
            this.cdr.detectChanges();
          }, 50);
        }
      });
    });

    this.intersectionObserver.observe(this.el.nativeElement);
  }

  private setupResizeObserver(): void {
    const svgContainer = this.el.nativeElement.querySelector('.svg-container');
    if (svgContainer && typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => {
        this.getActualWidth();
        this.cdr.detectChanges();
      });

      this.resizeObserver.observe(svgContainer);
    }
  }
  
  private getActualWidth(): void {
    // Pour l'élément avec le sélecteur .svg-container
    const svgContainer = this.el.nativeElement.querySelector('.svg-container');
    if (svgContainer) {
      // Récupérer la largeur calculée
      this.actualWidthInPx = svgContainer.offsetWidth;
    }
  }
  
  // Méthode publique pour récupérer la largeur à tout moment
  public getContainerWidthInPx(): number {
    this.getActualWidth();
    return this.actualWidthInPx;
  }
  
  public refresh() {

  }


  public setBodyItemIndice(indice: number): void {
    this.avatar.body = indice;
  }



  public setHatItemIndice(indice: number): void {
    this.avatar.hat = indice
  }


  public setMouthItemIndice(indice: number): void {
    this.avatar.mouth = indice
  }


  public setEyestItemIndice(indice: number): void {
    this.avatar.eyes = indice;
  }


  public setBodyColorIndice(indice: number): void {
    this.avatar.body_color = indice;
  }

  public setHatColorIndice(indice: number): void {
    this.avatar.hat_color = indice;
  }

  public setMouthColorIndice(indice: number): void {
    this.avatar.mouth_color = indice;
  }

  public setEyesColorIndice(indice: number): void {
    this.avatar.eyes_color = indice;
  }



  getHeigth(): number {
    return this.getContainerWidthInPx() * 640 / 480;
  }

  getSvgHeigth(): number {
    return this.getContainerWidthInPx() * 3.0 / 2.0;
  }

  getOffset(): number {
    return this.getSvgHeigth() - this.getHeigth();
  }

}